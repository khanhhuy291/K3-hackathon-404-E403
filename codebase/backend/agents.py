"""
Backend agents for Discord Course Assistant.

Architecture:
- RawJsonExtractorAgent: discord_message.json -> structured JSON.
- DeadlineReminderAgent: time/deadline/reminder tools.
- StructuredSearchAgent: search inside `codebase copy/structured_discord.json` and mirrors.
- AutoToolQAAgent: small tool-calling Q&A agent framework; can synthesize with NVIDIA/OpenAI-compatible Llama when configured, otherwise deterministic.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.request
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
CODEBASE_DIR = ROOT / "codebase"
DATA_FILE = ROOT / "discord_message.json"
RUNTIME_DIR = CODEBASE_DIR / "runtime"
RUNTIME_DATA_FILE = RUNTIME_DIR / "live_discord_messages.json"
STRUCTURED_FILE = CODEBASE_DIR / "structured_discord.json"
RUNTIME_STRUCTURED_FILE = RUNTIME_DIR / "structured_discord.json"
RUNTIME_STATUS_FILE = RUNTIME_DIR / "crawler_status.json"
COPY_STRUCTURED_FILE = ROOT / "codebase copy" / "structured_discord.json"
DEFAULT_TZ_OFFSET = "+07:00"
LOCAL_TZ = timezone(timedelta(hours=7))


def load_dotenv(path: Path = ROOT / ".env") -> Optional[Path]:
    """Load the root .env without overriding explicit process environment values."""
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if " #" in value and not value.startswith(("'", '"')):
            value = value.split(" #", 1)[0].rstrip()
        value = value.strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    return path


def atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """Atomically replace a JSON file so concurrent readers never see partial output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def raw_revision(raw: Dict[str, Any]) -> str:
    payload = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fix_mojibake_text(value: str) -> str:
    """Repair common UTF-8 Vietnamese text accidentally stored as Latin-1/CP1252."""
    if not isinstance(value, str):
        return value
    markers = ("Ã", "Ä", "Æ", "Â", "áº", "á»", "\ufffd")
    if not any(m in value for m in markers):
        return value
    try:
        repaired = value.encode("latin-1").decode("utf-8")
        old_score = sum(value.count(m) for m in markers)
        new_score = sum(repaired.count(m) for m in markers)
        return repaired if new_score <= old_score else value
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def repair_texts(obj: Any) -> Any:
    if isinstance(obj, str):
        return fix_mojibake_text(obj)
    if isinstance(obj, list):
        return [repair_texts(x) for x in obj]
    if isinstance(obj, dict):
        return {k: repair_texts(v) for k, v in obj.items()}
    return obj


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=LOCAL_TZ)
        return dt.astimezone(LOCAL_TZ)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M", "%H:%M %d/%m/%Y"):
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


def normalize_text(text: Any) -> str:
    text = fix_mojibake_text(str(text or "")).casefold()
    # Accent-insensitive search/intent routing: "g?n nh?t" -> "gan nhat".
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


class NvidiaOpenAIClient:
    """Tiny OpenAI-compatible client for NVIDIA NIM / Llama via urllib."""

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
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return json.loads(raw["choices"][0]["message"]["content"])

    def chat_text(self, system: str, user: str, timeout: int = 45) -> str:
        if not self.enabled:
            raise RuntimeError("Missing OPENAI_API_KEY/NVIDIA_API_KEY")
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return raw["choices"][0]["message"]["content"]


@dataclass
class RawJsonExtractorAgent:
    llm: NvidiaOpenAIClient

    def extract(self, raw: Dict[str, Any], prefer_llm: bool = True) -> Dict[str, Any]:
        if prefer_llm and self.llm.enabled:
            try:
                candidate = self._extract_with_llm(raw)
                return self._normalize(candidate, raw, source="llm_nvidia_openai_compatible")
            except Exception as exc:
                structured = self._extract_deterministic(raw)
                structured["metadata"]["llm_error"] = str(exc)[:300]
                return structured
        return self._extract_deterministic(raw)

    def _extract_with_llm(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "You are an intelligent course assistant information extraction AI. "
            "Convert raw Discord course messages into a structured JSON schema.\n"
            "STRICT CLASSIFICATION & SORTING RULES:\n"
            "1. DEADLINES: ONLY classify messages as deadlines if they contain an actual task submission requirement, assignment, quiz, lab, form due date, or project submission constraint (e.g. 'cổng nộp', 'hạn nộp', 'deadline', 'nộp bài', 'submit link', 'hạn nộp form'). Do NOT classify general resource shares, slide links, tutorial posts, or general chatter as deadlines.\n"
            "2. ANNOUNCEMENTS: Any official news, schedule changes, instructor updates, guidelines, or resource shares. Order announcements by message_time NEWEST FIRST.\n"
            "3. TIMESTAMP PRESERVATION: Always extract and preserve 'message_time' (the exact ISO timestamp when the text appeared) for EVERY item.\n"
            "4. OVERDUE ITEMS: Overdue deadlines MUST be placed at the VERY END of the deadlines array after all active/upcoming deadlines.\n"
            "Return valid JSON only matching schema: {metadata, announcements, deadlines, meetings, resources, documents, questions, timeline, stats}. Preserve IDs, channels, authors, timestamps, links, attachments."
        )
        return self.llm.chat_json(system, json.dumps(repair_texts(raw), ensure_ascii=False))

    def _iter_messages(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if isinstance(raw.get("messages"), list):
            rows.extend(dict(m) for m in raw.get("messages", []) if isinstance(m, dict))
        for ch in raw.get("channels", []) or []:
            channel_name = ch.get("channel") or ch.get("name") or "unknown"
            for m in ch.get("messages", []) or []:
                if isinstance(m, dict):
                    merged = dict(m)
                    merged.setdefault("channel", channel_name)
                    rows.append(merged)
        return rows

    def _base_item(self, server: str, m: Dict[str, Any]) -> Dict[str, Any]:
        mid = str(m.get("id", ""))
        channel = m.get("channel") or "unknown"
        message_server = m.get("server") or server
        return {
            "id": mid,
            "channel": channel,
            "author": m.get("author"),
            "role": m.get("role"),
            "message_time": iso(parse_dt(m.get("timestamp") or m.get("time") or m.get("created_at"))),
            "title": m.get("title"),
            "content": m.get("content", ""),
            "tags": m.get("tags", []) or [],
            "source_url": m.get("source_url") or m.get("jump_url") or message_url(message_server, channel, mid),
        }

    def _looks_like_deadline_text(self, text: str) -> bool:
        folded = normalize_text(text)
        if any(ex in folded for ex in ("frontend-slides", "vibecoding", "learning.aiecos.ai")):
            return False
        return any(k in folded for k in (
            "deadline", "han nop", "han cuoi", "nop bai", "nop link", "cong nop", "due date",
            "submission deadline", "thoi han nop", "commit spec", "han nop form", "han cung commit",
            "qua han", "gia han", "bai tap ve nha", "assignment"
        ))

    def _looks_urgent_text(self, text: str) -> bool:
        folded = (text or "").casefold()
        return any(k in folded for k in ("deadline", "hạn", "gấp", "khẩn", "urgent", "nhanh chóng", "ngay", "sớm"))

    def _sort_deadlines(self, deadlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for d in deadlines:
            dt = parse_dt(d.get("deadline_at") or d.get("deadline"))
            d["status"] = self._status(dt)
        active = [d for d in deadlines if d.get("status") != "overdue"]
        overdue = [d for d in deadlines if d.get("status") == "overdue"]

        active.sort(key=lambda x: (x.get("deadline_at") or "9999-99-99", x.get("message_time") or ""))
        overdue.sort(key=lambda x: (x.get("deadline_at") or "0000-00-00", x.get("message_time") or ""), reverse=True)
        return active + overdue

    def _extract_deterministic(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        raw = repair_texts(raw)
        server = raw.get("server", "Discord")
        messages = self._iter_messages(raw)
        announcements: List[Dict[str, Any]] = []
        deadlines: List[Dict[str, Any]] = []
        meetings: List[Dict[str, Any]] = []
        resources: List[Dict[str, Any]] = []
        documents: List[Dict[str, Any]] = []
        questions: List[Dict[str, Any]] = []
        timeline: List[Dict[str, Any]] = []

        for m in messages:
            base = self._base_item(server, m)
            content = base.get("content", "") or ""
            mtype = m.get("type", "message")
            timeline.append({**base, "type": mtype})

            norm_content = normalize_text(content)
            channel_norm = normalize_text(base.get("channel", ""))

            # Official / Course Announcements
            is_official_ch = any(c in channel_norm for c in ("thong bao", "announcement", "chung", "thoi gian", "tai lieu", "general"))
            is_instructor_role = str(base.get("role", "")).casefold() in ("mentor", "instructor", "admin", "ta")
            has_announcement_kws = any(k in norm_content for k in (
                "thong bao", "chao mung", "huong dan", "luu y", "quy trinh", "slide", "link", "form",
                "nop", "cong nop", "tai lieu", "demo", "checkpoint", "cp1", "cp2", "cp3", "cp4", "cp5"
            ))
            
            if mtype == "announcement" or is_official_ch or is_instructor_role or (has_announcement_kws and len(content.strip()) > 15):
                announcements.append({
                    **base,
                    "title": base.get("title") or self._infer_title(content, default="Thông báo khóa học"),
                    "priority": m.get("priority") or ("high" if self._looks_urgent_text(content) else "normal")
                })

            # Strict Deadline Matching: Only tasks with submission requirements
            deadline_signal = m.get("deadline") or mtype == "deadline" or self._looks_like_deadline_text(content)
            if deadline_signal:
                dt = parse_dt(m.get("deadline")) or self._deadline_from_text(content, base.get("message_time"))
                if not dt and self._looks_like_deadline_text(content) and base.get("message_time"):
                    dt = parse_dt(base.get("message_time"))
                
                if dt or m.get("deadline"):
                    deadlines.append({
                        **base,
                        "title": base.get("title") or self._infer_title(content, default="Hạn nộp bài"),
                        "deadline_at": iso(dt),
                        "status": self._status(dt),
                        "priority": m.get("priority") or ("high" if (dt and (dt - now_local()).total_seconds() <= 24 * 3600) or self._looks_urgent_text(content) else "normal"),
                        "raw_deadline": m.get("deadline") or content[:60],
                    })

            meeting = m.get("meeting") if isinstance(m.get("meeting"), dict) else {}
            if mtype in {"meeting", "workshop"} or meeting or m.get("meeting_time") or any(k in norm_content for k in ("zoom", "google meet", "lich hoc", "buoi hoc", "office hours")):
                mt = parse_dt(meeting.get("time") or m.get("meeting_time") or m.get("timestamp") or m.get("time"))
                meetings.append({
                    **base,
                    "title": base.get("title") or self._infer_title(content, default="Meeting / Buổi học"),
                    "meeting_at": iso(mt),
                    "platform": meeting.get("platform"),
                    "meeting_id": meeting.get("meeting_id"),
                    "passcode": meeting.get("passcode"),
                    "meeting_link": meeting.get("url") or m.get("meeting_link"),
                    "status": self._status(mt),
                })

            for link in m.get("links", []) or []:
                if isinstance(link, dict):
                    resources.append({**base, "title": link.get("title") or base.get("title") or self._infer_title(content, default="Link tài nguyên"), "url": link.get("url"), "kind": link.get("type") or mtype})

            for att in m.get("attachments", []) or []:
                if isinstance(att, dict):
                    doc = {**base, "name": att.get("name") or base.get("title") or "Attachment", "title": base.get("title") or att.get("name") or "Attachment", "url": att.get("url"), "kind": att.get("type") or mtype}
                    documents.append(doc)
                    resources.append({**doc, "title": doc["title"]})

            if mtype == "document" and not m.get("attachments"):
                documents.append({**base, "name": base.get("title") or "Document", "url": None, "kind": mtype})

            is_question = (
                mtype == "question" or "?" in content or
                any(k in norm_content for k in ("cho em hoi", "cho minh hoi", "cho hoi", "ai biet", "lam sao", "nhu nao", "giup em", "giup minh", "thac mac", "hoi ve"))
            )
            if is_question:
                questions.append({**base, "question": content, "reply_to": m.get("reply_to"), "answered": bool(m.get("answer") or m.get("answered"))})

        # Newest announcements first
        announcements.sort(key=lambda x: x.get("message_time") or "", reverse=True)
        timeline.sort(key=lambda x: x.get("message_time") or "", reverse=True)
        questions.sort(key=lambda x: x.get("message_time") or "", reverse=True)
        
        # Deadlines: Active/upcoming first, OVERDUE placed at the VERY END!
        deadlines = self._sort_deadlines(deadlines)
        meetings.sort(key=lambda x: x.get("meeting_at") or "9999")

        return {
            "metadata": {"server": server, "generated_at": now_local().isoformat(), "extractor": "deterministic_fallback", "source_file": DATA_FILE.name, "timezone": "Asia/Saigon", "schema_version": "1.1"},
            "announcements": announcements,
            "deadlines": deadlines,
            "meetings": meetings,
            "resources": resources,
            "documents": documents,
            "questions": questions,
            "timeline": timeline,
            "stats": {"messages": len(timeline), "announcements": len(announcements), "deadlines": len(deadlines), "meetings": len(meetings), "resources": len(resources), "documents": len(documents), "questions": len(questions)},
        }

    def _normalize(self, candidate: Dict[str, Any], raw: Dict[str, Any], source: str) -> Dict[str, Any]:
        fallback = self._extract_deterministic(raw)
        
        # Merge lists cleanly by message ID so nothing detected deterministically is lost
        for key in ("announcements", "deadlines", "meetings", "resources", "documents", "questions"):
            llm_list = candidate.get(key, [])
            if not isinstance(llm_list, list):
                llm_list = []
            
            existing_ids = {str(item.get("id")) for item in llm_list if isinstance(item, dict) and item.get("id")}
            for fb_item in fallback.get(key, []):
                fb_id = str(fb_item.get("id", ""))
                if fb_id and fb_id not in existing_ids:
                    llm_list.append(fb_item)
                    existing_ids.add(fb_id)
            candidate[key] = llm_list

        candidate["timeline"] = fallback["timeline"]
        candidate.setdefault("metadata", {})
        candidate["metadata"].update({
            "server": raw.get("server", candidate["metadata"].get("server", "Discord")),
            "generated_at": now_local().isoformat(),
            "extractor": source,
            "source_file": DATA_FILE.name,
            "timezone": "Asia/Saigon",
            "schema_version": "1.1"
        })
        
        # Sort announcements NEWEST FIRST
        if isinstance(candidate.get("announcements"), list):
            candidate["announcements"].sort(key=lambda x: x.get("message_time") or "", reverse=True)
            
        # Ensure status calculation for deadlines and place OVERDUE AT THE END!
        if isinstance(candidate.get("deadlines"), list):
            candidate["deadlines"] = self._sort_deadlines(candidate["deadlines"])

        # Update stats
        candidate["stats"] = {
            "messages": len(candidate.get("timeline", [])),
            "announcements": len(candidate.get("announcements", [])),
            "deadlines": len(candidate.get("deadlines", [])),
            "meetings": len(candidate.get("meetings", [])),
            "resources": len(candidate.get("resources", [])),
            "documents": len(candidate.get("documents", [])),
            "questions": len(candidate.get("questions", [])),
        }
        return candidate

    def _deadline_from_text(self, text: str, anchor_time: Optional[str] = None) -> Optional[datetime]:
        if not text:
            return None
        base_dt = parse_dt(anchor_time) or now_local()
        year = base_dt.year
        norm = normalize_text(text)
        
        # ISO timestamp match (2026-08-01 23:59 or 2026-08-01T23:59:00)
        m = re.search(r"(20\d{2}-\d{2}-\d{2})[ T](\d{1,2}(?::|h)\d{2})", text, re.I)
        if m:
            return parse_dt(f"{m.group(1)}T{m.group(2).replace('h', ':')}:00")
        
        # Time + Date match (23h59 ngày 01/08 or 01/08 lúc 23:59)
        time_pattern = r"(\d{1,2})(?::|h)(\d{2})"
        date_pattern = r"(?:ngày|ngay)?\s*(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?"
        
        m = re.search(rf"{time_pattern}\s*(?:lúc|luc)?\s*{date_pattern}", text, re.I)
        if m:
            hour, minute, day, month, y = m.groups()
            return parse_dt(f"{int(day):02d}/{int(month):02d}/{y or year} {hour}:{minute}")
            
        m = re.search(rf"{date_pattern}.{{0,24}}?(?:lúc|luc)?\s*{time_pattern}", text, re.I)
        if m:
            day, month, y, hour, minute = m.groups()
            return parse_dt(f"{int(day):02d}/{int(month):02d}/{y or year} {hour}:{minute}")
            
        # Relative day match (hôm nay, ngày mai, tối nay, đêm nay, ngày kia)
        time_match = re.search(time_pattern, text, re.I)
        hour_str = time_match.group(1) if time_match else "23"
        min_str = time_match.group(2) if time_match else "59"
        
        if any(w in norm for w in ("hom nay", "toi nay", "dem nay")):
            return base_dt.replace(hour=int(hour_str), minute=int(min_str), second=0, microsecond=0)
        if any(w in norm for w in ("ngay mai", "sang mai", "toi mai")):
            target = base_dt + timedelta(days=1)
            return target.replace(hour=int(hour_str), minute=int(min_str), second=0, microsecond=0)
        if "ngay kia" in norm:
            target = base_dt + timedelta(days=2)
            return target.replace(hour=int(hour_str), minute=int(min_str), second=0, microsecond=0)
            
        # Date-only match fallback (default time 23:59)
        m_date = re.search(r"(?:ngày|ngay)?\s*(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?", text, re.I)
        if m_date:
            day, month, y = m_date.groups()
            return parse_dt(f"{int(day):02d}/{int(month):02d}/{y or year} 23:59")
            
        return None

    def _infer_title(self, text: str, default: str = "Course item") -> str:
        if not text:
            return default
        cleaned = re.sub(r"https?://\S+", "", text, flags=re.I)
        cleaned = re.sub(r"[*_#~`]", "", cleaned)
        cleaned = re.sub(r"^(thông báo|deadline|chú ý|lưu ý|lịch học)[:\s-]*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .:-")
        if not cleaned:
            return default
        first_line = cleaned.split("\n")[0].split(". ")[0]
        return first_line[:90].strip() or default

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

    def latest_deadline(self, include_overdue: bool = False) -> Dict[str, Any]:
        """Return nearest upcoming deadline compared with current time."""
        n = now_local()
        candidates: List[Tuple[float, Dict[str, Any]]] = []
        for d in self.structured.get("deadlines", []):
            dt = parse_dt(d.get("deadline_at") or d.get("deadline"))
            if not dt:
                continue
            hours = (dt - n).total_seconds() / 3600
            if include_overdue or hours >= 0:
                candidates.append((hours, {**d, "hours_left": round(hours, 2), "status": "overdue" if hours < 0 else ("due_soon" if hours <= 24 else "upcoming")}))
        if not candidates:
            return {"now": n.isoformat(), "item": None, "message": "Không tìm thấy deadline phù hợp."}
        candidates.sort(key=lambda x: (abs(x[0]) if include_overdue else x[0]))
        item = candidates[0][1]
        return {"now": n.isoformat(), "item": item, "message": f"Deadline gần nhất là '{item.get('title')}' vào {item.get('deadline_at')} (còn {item.get('hours_left')} giờ)."}

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
        if tool in {"latest_deadline", "get_latest_deadline"}:
            return self.latest_deadline(bool(kwargs.get("include_overdue", False)))
        if tool == "make_reminders":
            return self.make_reminders(int(kwargs.get("within_hours", 72)))
        return {"error": f"Unknown tool: {tool}", "available_tools": ["get_current_time", "check_deadlines", "latest_deadline", "make_reminders"]}


@dataclass
class StructuredSearchAgent:
    """Search tools targeting `codebase copy/structured_discord.json`."""
    path: Path = COPY_STRUCTURED_FILE

    def load(self) -> Dict[str, Any]:
        source = RUNTIME_STRUCTURED_FILE if RUNTIME_STRUCTURED_FILE.exists() else self.path
        return repair_texts(_load_json_file(source))

    def flatten(self, data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        data = data or self.load()
        rows: List[Dict[str, Any]] = []
        for section in ("deadlines", "announcements", "meetings", "resources", "documents", "questions", "timeline"):
            for item in data.get(section, []) or []:
                if isinstance(item, dict):
                    rows.append({"section": section, **item})
        return rows

    def search(self, query: str = "", sections: Optional[List[str]] = None, limit: int = 10) -> Dict[str, Any]:
        q = normalize_text(query)
        tokens = [t for t in re.split(r"\W+", q) if t]
        results = []
        for item in self.flatten():
            if sections and item.get("section") not in sections:
                continue
            hay = normalize_text(" ".join(json.dumps(v, ensure_ascii=False) for v in item.values()))
            score = 0
            if q and q in hay:
                score += 5
            score += sum(1 for t in tokens if t in hay)
            if not q or score > 0:
                results.append({"score": score, "item": item})
        results.sort(key=lambda x: (-x["score"], x["item"].get("deadline_at") or x["item"].get("message_time") or ""))
        return {"query": query, "source_file": str(self.path), "count": len(results), "results": results[:limit]}

    def search_deadlines(self, query: str = "", limit: int = 10) -> Dict[str, Any]:
        return self.search(query=query, sections=["deadlines"], limit=limit)

    def search_crawled_json(self, query: str = "", channel: str = "", author: str = "", limit: int = 10) -> Dict[str, Any]:
        """Direct non-RAG search inside raw crawled Discord messages JSON."""
        raw_data = load_raw()
        messages = raw_data.get("messages", [])
        q = normalize_text(query)
        channel_filter = normalize_text(channel)
        author_filter = normalize_text(author)
        tokens = [t for t in re.split(r"\W+", q) if t]
        
        matched_results = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            msg_channel = normalize_text(msg.get("channel", ""))
            msg_author = normalize_text(msg.get("author", ""))
            
            if channel_filter and channel_filter not in msg_channel:
                continue
            if author_filter and author_filter not in msg_author:
                continue
                
            haystack = normalize_text(" ".join([
                str(msg.get("content", "")),
                str(msg.get("channel", "")),
                str(msg.get("author", "")),
                " ".join(str(l.get("url", "")) for l in msg.get("links", []) if isinstance(l, dict))
            ]))
            
            score = 0
            if q and q in haystack:
                score += 10
            score += sum(2 for t in tokens if t in haystack)
            
            if not q or score > 0:
                matched_results.append({
                    "score": score,
                    "id": msg.get("id"),
                    "channel": msg.get("channel"),
                    "author": msg.get("author"),
                    "time": msg.get("timestamp") or msg.get("created_at"),
                    "content": msg.get("content"),
                    "links": msg.get("links", []),
                    "attachments": msg.get("attachments", []),
                    "source_url": msg.get("source_url") or msg.get("jump_url")
                })

        matched_results.sort(key=lambda x: (-x["score"], x.get("time") or ""), reverse=False)
        return {
            "query": query,
            "channel_filter": channel,
            "author_filter": author,
            "total_matches": len(matched_results),
            "results": matched_results[:limit]
        }


GITHUB_LABS_FILE = RUNTIME_DIR / "github_labs.json"

@dataclass
class GitHubLabsAgent:
    """Agent and tools for querying VinUni-AI20k GitHub Repositories & Labs."""
    file_path: Path = GITHUB_LABS_FILE

    def load_labs(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists() or self.file_path.stat().st_size == 0:
            return []
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            return data.get("labs", [])
        except Exception:
            return []

    def list_available_labs(self, cohort: str = "") -> Dict[str, Any]:
        labs = self.load_labs()
        filter_c = normalize_text(cohort)
        results = []
        for lab in labs:
            name = lab.get("name", "")
            if filter_c and filter_c not in normalize_text(name):
                continue
            results.append({
                "name": name,
                "url": lab.get("url"),
                "description": lab.get("description") or "Bài lab khóa học VinUni-AI20k",
                "pushed_at": lab.get("pushed_at")
            })
        return {"cohort_filter": cohort, "total_labs": len(results), "labs": results}

    def search_labs(self, query: str = "", lab_name: str = "", limit: int = 5) -> Dict[str, Any]:
        labs = self.load_labs()
        q = normalize_text(query)
        target_name = normalize_text(lab_name)
        tokens = [t for t in re.split(r"\W+", q) if t]
        
        matches = []
        for lab in labs:
            name = lab.get("name", "")
            if target_name and target_name not in normalize_text(name):
                continue
            readme = lab.get("readme_full", "") or lab.get("readme_snippet", "")
            haystack = normalize_text(f"{name} {lab.get('description', '')} {readme}")
            
            score = 0
            if q and q in haystack:
                score += 10
            score += sum(2 for t in tokens if t in haystack)
            
            if not q or score > 0:
                matches.append({
                    "score": score,
                    "name": name,
                    "url": lab.get("url"),
                    "snippet": readme[:350] + "..." if len(readme) > 350 else readme,
                    "readme_full": readme
                })
        matches.sort(key=lambda x: -x["score"])
        return {"query": query, "lab_name_filter": lab_name, "count": len(matches), "results": matches[:limit]}


@dataclass
class ToolSpec:
    name: str
    description: str
    func: Callable[..., Dict[str, Any]]


class MiniToolAgentFramework:
    def __init__(self, tools: List[ToolSpec]) -> None:
        self.tools = {t.name: t for t in tools}

    def call(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        if name not in self.tools:
            return {"error": f"Unknown tool {name}", "available_tools": list(self.tools)}
        return self.tools[name].func(**kwargs)

    def list_tools(self) -> List[Dict[str, str]]:
        return [{"name": t.name, "description": t.description} for t in self.tools.values()]


class AutoToolQAAgent:
    """Q&A agent that automatically calls search/time/deadline/lab tools before answering."""

    def __init__(self, structured: Dict[str, Any]) -> None:
        self.structured = structured
        self.deadline_agent = DeadlineReminderAgent(structured)
        self.search_agent = StructuredSearchAgent()
        self.labs_agent = GitHubLabsAgent()
        self.llm = NvidiaOpenAIClient()
        self.framework = MiniToolAgentFramework([
            ToolSpec("get_current_time", "Lấy thời gian hiện tại Asia/Saigon", lambda: self.deadline_agent.get_current_time()),
            ToolSpec("list_available_labs", "Liệt kê danh sách các bài lab hiện có trên GitHub VinUni-AI20k", lambda cohort="": self.labs_agent.list_available_labs(cohort)),
            ToolSpec("search_github_labs", "Tìm kiếm và đọc nội dung hướng dẫn chi tiết bài lab từ GitHub VinUni-AI20k", lambda query="", lab_name="", limit=5: self.labs_agent.search_labs(query, lab_name, int(limit))),
            ToolSpec("search_crawled_json", "Tìm kiếm trực tiếp từ vựng/nội dung trong dữ liệu Discord JSON crawl thô (No-RAG)", lambda query="", channel="", author="", limit=10: self.search_agent.search_crawled_json(query, channel, author, int(limit))),
            ToolSpec("search_structured_json", "Search trong codebase copy/structured_discord.json", lambda query="", limit=10: self.search_agent.search(query, limit=int(limit))),
            ToolSpec("search_deadlines", "Search deadline trong structured JSON", lambda query="", limit=10: self.search_agent.search_deadlines(query, int(limit))),
            ToolSpec("latest_deadline", "Lấy deadline gần nhất so với thời gian hiện tại", lambda include_overdue=False: self.deadline_agent.latest_deadline(bool(include_overdue))),
            ToolSpec("check_deadlines", "Kiểm tra deadline trong N giờ tới", lambda within_hours=72: self.deadline_agent.check_deadlines(int(within_hours))),
        ])



    def answer(self, question: str) -> Dict[str, Any]:
        q = normalize_text(question)
        tool_trace: List[Dict[str, Any]] = []

        # Always get current time first so deadline answers are time-aware.
        current_time = self.framework.call("get_current_time")
        tool_trace.append({"tool": "get_current_time", "args": {}, "result": current_time})

        if any(k in q for k in ["deadline mới", "deadline gan", "deadline gần", "gần nhất", "mới nhất", "tiếp theo", "next deadline", "latest deadline"]):
            latest = self.framework.call("latest_deadline")
            tool_trace.append({"tool": "latest_deadline", "args": {}, "result": latest})
            item = latest.get("item")
            if item:
                answer = f"Deadline gần nhất hiện tại là **{item.get('title')}** lúc **{item.get('deadline_at')}**. Còn khoảng **{item.get('hours_left')} giờ**. Nội dung: {item.get('content')}"
            else:
                answer = latest.get("message")
            return {"question": question, "answer": answer, "tool_trace": tool_trace, "tools": self.framework.list_tools()}

        if any(k in q for k in ["lab", "bai lab", "bài lab", "github lab", "danh sach lab", "danh sách lab"]):
            res_labs = self.framework.call("search_github_labs", query=question, limit=5)
            tool_trace.append({"tool": "search_github_labs", "args": {"query": question, "limit": 5}, "result": res_labs})
            if not res_labs.get("results"):
                res_all = self.framework.call("list_available_labs")
                tool_trace.append({"tool": "list_available_labs", "args": {}, "result": res_all})
        elif any(k in q for k in ["deadline", "hạn", "han"]):
            res = self.framework.call("search_deadlines", query=question, limit=5)
            tool_trace.append({"tool": "search_deadlines", "args": {"query": question, "limit": 5}, "result": res})
        else:
            res = self.framework.call("search_crawled_json", query=question, limit=5)
            tool_trace.append({"tool": "search_crawled_json", "args": {"query": question, "limit": 5}, "result": res})
            if not res.get("results"):
                res_fallback = self.framework.call("search_structured_json", query=question, limit=5)
                tool_trace.append({"tool": "search_structured_json", "args": {"query": question, "limit": 5}, "result": res_fallback})

        answer = self._deterministic_answer(question, tool_trace[-1]["result"])
        if self.llm.enabled:
            try:
                answer = self._llm_answer(question, tool_trace)
            except Exception as exc:
                tool_trace.append({"tool": "llm_synthesis", "args": {}, "error": str(exc)[:300]})
        return {"question": question, "answer": answer, "tool_trace": tool_trace, "tools": self.framework.list_tools()}

    def _deterministic_answer(self, question: str, search_result: Dict[str, Any]) -> str:
        if "labs" in search_result:
            labs = search_result.get("labs", [])
            lines = [f"📚 Danh sách bài Lab VinUni-AI20k ({search_result.get('total_labs')} repos):"]
            for l in labs[:10]:
                lines.append(f"• **{l.get('name')}**: {l.get('url')}")
            return "\n".join(lines)
            
        results = search_result.get("results", [])
        if not results:
            return "Mình chưa tìm thấy thông tin phù hợp trong dữ liệu."

        if results and "snippet" in results[0]:
            lines = ["📚 Tìm thấy hướng dẫn bài Lab trên GitHub:"]
            for r in results[:3]:
                lines.append(f"• **{r.get('name')}**\n  🔗 Link: {r.get('url')}\n  📝 Hướng dẫn: {r.get('snippet')[:200]}...")
            return "\n".join(lines)

        lines = ["Mình tìm thấy thông tin liên quan từ dữ liệu crawl JSON:"]
        for r in results[:5]:
            item = r.get("item") or r
            title = item.get("title") or item.get("name") or item.get("author") or "Thông tin"
            channel = item.get("channel") or item.get("section") or "kênh"
            when = item.get("deadline_at") or item.get("meeting_at") or item.get("time") or item.get("message_time") or "chưa rõ thời gian"
            content = str(item.get("content") or item.get("question") or item.get("url") or "")
            if len(content) > 150:
                content = content[:150] + "..."
            lines.append(f"• [#{channel}] {title} ({when}): {content}")
        return "\n".join(lines)



    def _llm_answer(self, question: str, tool_trace: List[Dict[str, Any]]) -> str:
        system = "Bạn là trợ lý khóa học. Trả lời ngắn gọn bằng tiếng Việt dựa trên tool results. Không bịa thông tin."
        user = json.dumps({"question": question, "tool_trace": tool_trace}, ensure_ascii=False, indent=2)
        return self.llm.chat_text(system, user)


def _load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _message_rows(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    return RawJsonExtractorAgent(NvidiaOpenAIClient())._iter_messages(raw)


def load_raw() -> Dict[str, Any]:
    """Return the synthetic fixture plus any ignored live Discord crawl records."""
    fixture = _load_json_file(DATA_FILE)
    live = _load_json_file(RUNTIME_DATA_FILE)
    messages = _message_rows(fixture)
    seen_ids = {str(message.get("id")) for message in messages if message.get("id") is not None}

    for message in _message_rows(live):
        message_id = str(message.get("id", ""))
        if message_id and message_id in seen_ids:
            continue
        messages.append(message)
        if message_id:
            seen_ids.add(message_id)

    return {
        "server": fixture.get("server") or live.get("server") or "Discord",
        "messages": messages,
        "source_files": [str(DATA_FILE), str(RUNTIME_DATA_FILE)] if live else [str(DATA_FILE)],
    }


def sync_copy_structured(structured: Dict[str, Any]) -> None:
    """Keep the legacy fixture-mode search mirror usable."""
    atomic_write_json(COPY_STRUCTURED_FILE, structured)


def _write_structured_cache(structured: Dict[str, Any]) -> None:
    target = RUNTIME_STRUCTURED_FILE if RUNTIME_DATA_FILE.exists() else STRUCTURED_FILE
    atomic_write_json(target, structured)


def get_structured(refresh: bool = False, prefer_llm: Optional[bool] = None, sync_copy: bool = True) -> Dict[str, Any]:
    raw = load_raw()
    revision = raw_revision(raw)
    cache_file = RUNTIME_STRUCTURED_FILE if RUNTIME_DATA_FILE.exists() else STRUCTURED_FILE
    if cache_file.exists() and not refresh:
        cached = repair_texts(_load_json_file(cache_file))
        cache_matches_raw = cached.get("metadata", {}).get("raw_revision") == revision
        if cached.get("stats", {}).get("messages", 0) > 0 and (cache_matches_raw or not RUNTIME_DATA_FILE.exists()):
            return cached
    agent = RawJsonExtractorAgent(NvidiaOpenAIClient())
    if prefer_llm is None:
        prefer_llm = agent.llm.enabled
    structured = agent.extract(raw, prefer_llm=prefer_llm)
    structured.setdefault("metadata", {})["raw_revision"] = revision
    _write_structured_cache(structured)
    if sync_copy and not RUNTIME_DATA_FILE.exists():
        sync_copy_structured(structured)
    return structured

