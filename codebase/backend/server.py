"""HTTP backend for Discord Course Assistant.

No external dependency required. It serves:
- backend API under /api/*
- split frontend from codebase/frontend
"""
from __future__ import annotations

import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from agents import (
    AutoToolQAAgent,
    DeadlineReminderAgent,
    StructuredSearchAgent,
    get_structured,
    load_raw,
)
from discord_ingestion import crawler_status

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "codebase" / "frontend"


class ApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _send_json(self, obj: Any, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json({"ok": True})

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": raw}

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            body = self._read_json_body()
            if parsed.path == "/api/qa":
                question = str(body.get("question") or body.get("q") or "").strip()
                if not question:
                    return self._send_json({"error": "Missing question"}, status=400)
                return self._send_json(AutoToolQAAgent(get_structured()).answer(question))
            return self._send_json({"error": f"Unknown POST route {parsed.path}"}, status=404)
        except Exception as exc:
            return self._send_json({"error": str(exc)}, status=500)

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
            if parsed.path == "/api/crawler/status":
                return self._send_json(crawler_status())
            if parsed.path == "/api/time":
                return self._send_json(DeadlineReminderAgent(get_structured()).get_current_time())
            if parsed.path == "/api/deadlines/check":
                hours = int(qs.get("hours", ["72"])[0])
                return self._send_json(DeadlineReminderAgent(get_structured()).check_deadlines(hours))
            if parsed.path == "/api/deadlines/latest":
                include_overdue = qs.get("include_overdue", ["0"])[0] == "1"
                return self._send_json(DeadlineReminderAgent(get_structured()).latest_deadline(include_overdue))
            if parsed.path == "/api/reminders":
                hours = int(qs.get("hours", ["72"])[0])
                return self._send_json(DeadlineReminderAgent(get_structured()).make_reminders(hours))
            if parsed.path == "/api/search":
                q = qs.get("q", [""])[0]
                limit = int(qs.get("limit", ["10"])[0])
                section = qs.get("section", [""])[0]
                sections = [section] if section else None
                return self._send_json(StructuredSearchAgent().search(q, sections=sections, limit=limit))
            if parsed.path == "/api/qa":
                question = qs.get("q", [""])[0]
                if not question:
                    return self._send_json({"error": "Missing q"}, status=400)
                return self._send_json(AutoToolQAAgent(get_structured()).answer(question))
            if parsed.path == "/api/agent/tool":
                tool = qs.get("tool", [""])[0]
                hours = int(qs.get("hours", ["72"])[0])
                include_overdue = qs.get("include_overdue", ["0"])[0] == "1"
                return self._send_json(DeadlineReminderAgent(get_structured()).run_tool(tool, within_hours=hours, include_overdue=include_overdue))
            return super().do_GET()
        except Exception as exc:
            return self._send_json({"error": str(exc)}, status=500)


def start_background_bots() -> None:
    # 1. Start Telegram Bot if configured in .env
    try:
        from telegram_bot import TelegramBotListener
        tb = TelegramBotListener()
        if tb.enabled:
            t_tg = threading.Thread(target=tb.run, daemon=True)
            t_tg.start()
            print("[App Launcher] Telegram Bot listener started in background thread.")
        else:
            print("[App Launcher] Telegram Bot: Set TELEGRAM_BOT_TOKEN in .env to enable Telegram Bot & Q&A.")
    except Exception as exc:
        print(f"[App Launcher] Could not start Telegram Bot: {exc}")

    # 2. Start Discord Bot if configured in .env
    try:
        import discord_bot
        token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        if token:
            def _run_discord() -> None:
                try:
                    bot = discord_bot.create_bot()
                    bot.run(token)
                except Exception as e:
                    print(f"[App Launcher] Discord Bot exited: {e}")
            t_disc = threading.Thread(target=_run_discord, daemon=True)
            t_disc.start()
            print("[App Launcher] Discord Bot crawler started in background thread.")
    except Exception as exc:
        print(f"[App Launcher] Could not start Discord Bot: {exc}")


def main() -> None:
    refresh = "--refresh" in sys.argv
    use_llm = "--llm" in sys.argv
    if "extract" in sys.argv:
        structured = get_structured(refresh=True, prefer_llm=use_llm)
        print(json.dumps(structured, ensure_ascii=False, indent=2))
        return
    get_structured(refresh=refresh, prefer_llm=use_llm)
    port = int(os.getenv("PORT", "8000"))
    print(f"Backend API + frontend serving: http://localhost:{port}")
    print(f"Frontend dir: {FRONTEND_DIR}")
    print("APIs: /api/structured, /api/crawler/status, /api/search?q=deadline, /api/qa?q=deadline gần nhất")
    
    start_background_bots()
    ThreadingHTTPServer(("", port), ApiHandler).serve_forever()


if __name__ == "__main__":
    main()

