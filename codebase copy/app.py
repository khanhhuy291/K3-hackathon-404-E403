"""
Discord Course Assistant prototype
- Agent 1: RawJsonExtractorAgent converts crawled Discord JSON into structured JSON.
- Agent 2: DeadlineReminderAgent exposes tools: current time, deadline checking, reminders.

Runs with only Python standard library. If NVIDIA/OpenAI-compatible credentials exist,
the extractor can call a Llama model through the OpenAI-compatible Chat Completions API.
Otherwise it falls back to deterministic local extraction.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "discord_message.json"
STRUCTURED_FILE = ROOT / "codebase" / "structured_discord.json"
STATIC_DIR = ROOT / "codebase" / "static"
DEFAULT_TZ_OFFSET = "+07:00"  # Asia/Saigon
LOCAL_TZ = timezone(timedelta(hours=7))


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc).astimezone(timezone.utc)
            # Treat source timestamps as local course timestamps; expose ISO without changing wall time.
            return datetime.fromisoformat(text + DEFAULT_TZ_OFFSET)
        return dt
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).replace(tzinfo=LOCAL_TZ)
            except ValueError:
                pass
    return None


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def message_url(server: str, channel: str, msg_id: str) -> str:
    return f"discord://{server.replace(' ', '-')}/{channel}/{msg_id}"


class NvidiaOpenAIClient:
    """Tiny OpenAI-compatible client using urllib; no external dependency needed."""

    def __init__(self) -> None:
        load_dotenv()
        self.api_key = (os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY") or "").strip()
        self.base_url = (os.getenv("OPENAI_BASE_URL") or "https://integrate.api.nvidia.com/v1").strip().rstrip("/")
        self.model = (os.getenv("OPENAI_MODEL") or "meta/llama-3.1-70b-instruct").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def chat_json(self, system: str, user: str, timeout: int = 45) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Missing OPENAI_API_KEY/NVIDIA_API_KEY")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"]
        return json.loads(content)


@dataclass
class RawJsonExtractorAgent:
    llm: NvidiaOpenAIClient

    def extract(self, raw: Dict[str, Any], prefer_llm: bool = True) -> Dict[str, Any]:
        """Return structured course JSON. Uses LLM if configured, validates and repairs locally."""
        if prefer_llm and self.llm.enabled:
            try:
                candidate = self._extract_with_llm(raw)
                return self._normalize(candidate, raw, source="llm_nvidia_openai_compatible")
            except Exception as exc:  # keep prototype robust for demo
                structured = self._extract_deterministic(raw)
                structured["metadata"]["llm_error"] = str(exc)[:300]
                return structured
        return self._extract_deterministic(raw)

    def _extract_with_llm(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "You are an information extraction agent. Convert Discord course crawl JSON "
            "into a compact structured JSON object. Return JSON only. Required top-level keys: "
            "metadata, announcements, deadlines, meetings, resources, documents, questions, timeline, stats. "
            "Preserve IDs, channel, author, timestamps, links, attachments, and infer deadline titles from content."
        )
        user = json.dumps(raw, ensure_ascii=False)
        return self.llm.chat_json(system, user)

    def _extract_deterministic(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        server = raw.get("server", "Discord")
        announcements: List[Dict[str, Any]] = []
        deadlines: List[Dict[str, Any]] = []
        meetings: List[Dict[str, Any]] = []
        resources: List[Dict[str, Any]] = []
        documents: List[Dict[str, Any]] = []
        questions: List[Dict[str, Any]] = []
        timeline: List[Dict[str, Any]] = []

        for ch in raw.get("channels", []):
            channel = ch.get("channel", "unknown")
            for m in ch.get("messages", []):
                mid = m.get("id", "")
                content = m.get("content", "")
                base = {
                    "id": mid,
                    "channel": channel,
                    "author": m.get("author"),
                    "message_time": m.get("time"),
                    "content": content,
                    "source_url": message_url(server, channel, mid),
                }
                mtype = m.get("type", "message")
                timeline.append({**base, "type": mtype})

                if mtype == "announcement":
                    announcements.append({**base, "priority": "high" if "deadline" in content.lower() else "normal"})
                if m.get("deadline") or re.search(r"deadline|hạn|due", content, re.I):
                    dt = parse_dt(m.get("deadline")) or self._deadline_from_text(content)
                    deadlines.append({
                        **base,
                        "title": self._infer_title(content),
                        "deadline_at": iso(dt),
                        "status": self._status(dt),
                        "raw_deadline": m.get("deadline"),
                    })
                if mtype == "meeting" or m.get("meeting_time"):
                    mt = parse_dt(m.get("meeting_time"))
                    meetings.append({
                        **base,
                        "title": self._infer_title(content, default="Meeting"),
                        "meeting_at": iso(mt),
                        "meeting_link": m.get("meeting_link"),
                        "status": self._status(mt),
                    })
                if m.get("links"):
                    for link in m.get("links", []):
                        resources.append({**base, "title": link.get("title") or self._infer_title(content), "url": link.get("url"), "kind": mtype})
                if m.get("attachments"):
                    for att in m.get("attachments", []):
                        documents.append({**base, "name": att.get("name"), "url": att.get("url"), "kind": mtype})
                if mtype == "question":
                    questions.append({**base, "answered": False})

        timeline.sort(key=lambda x: x.get("message_time") or "")
        return {
            "metadata": {
                "server": server,
                "generated_at": now_local().isoformat(),
                "extractor": "deterministic_fallback",
                "source_file": str(DATA_FILE.name),
            },
            "announcements": announcements,
            "deadlines": sorted(deadlines, key=lambda x: x.get("deadline_at") or "9999"),
            "meetings": sorted(meetings, key=lambda x: x.get("meeting_at") or "9999"),
            "resources": resources,
            "documents": documents,
            "questions": questions,
            "timeline": timeline,
            "stats": {
                "channels": len(raw.get("channels", [])),
                "messages": len(timeline),
                "announcements": len(announcements),
                "deadlines": len(deadlines),
                "meetings": len(meetings),
                "resources": len(resources),
                "documents": len(documents),
                "questions": len(questions),
            },
        }

    def _normalize(self, candidate: Dict[str, Any], raw: Dict[str, Any], source: str) -> Dict[str, Any]:
        fallback = self._extract_deterministic(raw)
        for key, default in fallback.items():
            candidate.setdefault(key, default)
        candidate.setdefault("metadata", {})
        candidate["metadata"].update({
            "server": raw.get("server", candidate["metadata"].get("server", "Discord")),
            "generated_at": now_local().isoformat(),
            "extractor": source,
            "source_file": DATA_FILE.name,
        })
        # Ensure deadline statuses are fresh.
        for d in candidate.get("deadlines", []):
            d["status"] = self._status(parse_dt(d.get("deadline_at") or d.get("deadline")))
        return candidate

    def _deadline_from_text(self, text: str) -> Optional[datetime]:
        m = re.search(r"(20\d{2}-\d{2}-\d{2})[ T](\d{1,2}:\d{2})", text)
        if m:
            return parse_dt(f"{m.group(1)}T{m.group(2)}:00")
        return None

    def _infer_title(self, text: str, default: str = "Course item") -> str:
        cleaned = re.sub(r"deadline:?\s*20\d{2}-\d{2}-\d{2}[^.]*", "", text, flags=re.I).strip(" .")
        cleaned = re.sub(r"submission deadline extended to .*", "submission", cleaned, flags=re.I).strip(" .")
        return cleaned[:80] or default

    def _status(self, dt: Optional[datetime]) -> str:
        if not dt:
            return "unknown"
        delta = dt - now_local()
        if delta.total_seconds() < 0:
            return "overdue"
        if delta.total_seconds() <= 24 * 3600:
            return "due_soon"
        return "upcoming"


@dataclass
class DeadlineReminderAgent:
    structured: Dict[str, Any]

    def get_current_time(self) -> Dict[str, str]:
        n = now_local()
        return {"now": n.isoformat(), "timezone": "Asia/Saigon", "date": n.date().isoformat(), "time": n.strftime("%H:%M:%S")}

    def check_deadlines(self, within_hours: int = 72) -> Dict[str, Any]:
        n = now_local()
        rows = []
        for d in self.structured.get("deadlines", []):
            dt = parse_dt(d.get("deadline_at") or d.get("deadline"))
            if not dt:
                continue
            hours = (dt - n).total_seconds() / 3600
            if hours <= within_hours:
                rows.append({**d, "hours_left": round(hours, 2), "status": "overdue" if hours < 0 else ("due_soon" if hours <= 24 else "upcoming")})
        return {"now": n.isoformat(), "within_hours": within_hours, "items": sorted(rows, key=lambda x: x["hours_left"])}

    def make_reminders(self, within_hours: int = 72) -> Dict[str, Any]:
        checked = self.check_deadlines(within_hours)
        reminders = []
        for d in checked["items"]:
            title = d.get("title") or "Deadline"
            if d["hours_left"] < 0:
                msg = f"Quá hạn: {title} ({d.get('deadline_at')})."
                level = "danger"
            elif d["hours_left"] <= 24:
                msg = f"Gấp: còn {d['hours_left']} giờ để hoàn thành {title}."
                level = "warning"
            else:
                msg = f"Sắp tới: {title} còn {d['hours_left']} giờ."
                level = "info"
            reminders.append({"deadline_id": d.get("id"), "level": level, "message": msg, "deadline_at": d.get("deadline_at")})
        return {**checked, "reminders": reminders}

    def run_tool(self, tool: str, **kwargs: Any) -> Dict[str, Any]:
        if tool == "get_current_time":
            return self.get_current_time()
        if tool == "check_deadlines":
            return self.check_deadlines(int(kwargs.get("within_hours", 72)))
        if tool == "make_reminders":
            return self.make_reminders(int(kwargs.get("within_hours", 72)))
        return {"error": f"Unknown tool: {tool}", "available_tools": ["get_current_time", "check_deadlines", "make_reminders"]}


def load_raw() -> Dict[str, Any]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def get_structured(refresh: bool = False, prefer_llm: bool = False) -> Dict[str, Any]:
    if STRUCTURED_FILE.exists() and not refresh:
        return json.loads(STRUCTURED_FILE.read_text(encoding="utf-8"))
    agent = RawJsonExtractorAgent(NvidiaOpenAIClient())
    structured = agent.extract(load_raw(), prefer_llm=prefer_llm)
    STRUCTURED_FILE.write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
    return structured


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, obj: Any, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/raw":
                return self._send_json(load_raw())
            if parsed.path == "/api/structured":
                refresh = qs.get("refresh", ["0"])[0] == "1"
                prefer_llm = qs.get("llm", ["0"])[0] == "1"
                return self._send_json(get_structured(refresh=refresh, prefer_llm=prefer_llm))
            if parsed.path == "/api/time":
                return self._send_json(DeadlineReminderAgent(get_structured()).get_current_time())
            if parsed.path == "/api/deadlines/check":
                hours = int(qs.get("hours", ["72"])[0])
                return self._send_json(DeadlineReminderAgent(get_structured()).check_deadlines(hours))
            if parsed.path == "/api/reminders":
                hours = int(qs.get("hours", ["72"])[0])
                return self._send_json(DeadlineReminderAgent(get_structured()).make_reminders(hours))
            return super().do_GET()
        except Exception as exc:
            return self._send_json({"error": str(exc)}, status=500)


def main() -> None:
    refresh = "--refresh" in sys.argv
    use_llm = "--llm" in sys.argv
    if "extract" in sys.argv:
        structured = get_structured(refresh=True, prefer_llm=use_llm)
        print(json.dumps(structured, ensure_ascii=False, indent=2))
        return
    get_structured(refresh=refresh, prefer_llm=use_llm)
    port = int(os.getenv("PORT", "8000"))
    print(f"Serving http://localhost:{port}")
    print("APIs: /api/structured, /api/reminders?hours=72, /api/time")
    ThreadingHTTPServer(("", port), AppHandler).serve_forever()


if __name__ == "__main__":
    main()


