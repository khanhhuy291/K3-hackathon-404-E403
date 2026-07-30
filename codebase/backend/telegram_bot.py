"""Telegram Bot integration for Discord Course Assistant.

Provides:
1. Instant push notifications for urgent Discord announcements/deadlines.
2. Q&A Chatbot for Telegram users connected to AutoToolQAAgent and Deadline tools.

Dependencies: standard library urllib (no external pip package required).
Set TELEGRAM_BOT_TOKEN and optional TELEGRAM_CHAT_ID in root .env.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agents import (
    AutoToolQAAgent,
    DeadlineReminderAgent,
    atomic_write_json,
    get_structured,
    load_dotenv,
    normalize_text,
    now_local,
    repair_texts,
)

SUBSCRIBERS_FILE = BACKEND_DIR.parent / "runtime" / "telegram_subscribers.json"


def _get_token_and_chat_id() -> Tuple[str, str]:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id


def _read_subscribers() -> Set[str]:
    subscribers = set()
    token, env_chat_id = _get_token_and_chat_id()
    if env_chat_id:
        subscribers.add(env_chat_id)
    if SUBSCRIBERS_FILE.exists() and SUBSCRIBERS_FILE.stat().st_size > 0:
        try:
            data = json.loads(SUBSCRIBERS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                subscribers.update(str(cid) for cid in data)
        except Exception:
            pass
    return subscribers


def _save_subscriber(chat_id: str) -> None:
    subscribers = _read_subscribers()
    subscribers.add(str(chat_id))
    SUBSCRIBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(SUBSCRIBERS_FILE, sorted(list(subscribers)))


def send_telegram_notification(text: str, chat_id: Optional[str] = None) -> bool:
    """Send text message to specific chat_id or all registered Telegram subscribers."""
    token, env_chat_id = _get_token_and_chat_id()
    if not token:
        print("[Telegram] No TELEGRAM_BOT_TOKEN found in .env")
        return False

    targets = [chat_id] if chat_id else list(_read_subscribers())
    if not targets and env_chat_id:
        targets = [env_chat_id]

    if not targets:
        print("[Telegram] No target TELEGRAM_CHAT_ID specified or subscribed.")
        return False

    success_count = 0
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    for target in targets:
        payload = {
            "chat_id": target,
            "text": text,
            "disable_web_page_preview": True,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                if res_data.get("ok"):
                    success_count += 1
        except Exception as exc:
            print(f"[Telegram] Failed to send message to {target}: {exc}")

    return success_count > 0


def notify_urgent_discord_message(raw_msg: Dict[str, Any]) -> None:
    """Format and send notification when a Discord announcement/deadline arrives."""
    token, _ = _get_token_and_chat_id()
    if not token:
        return

    content = str(raw_msg.get("content", "")).strip()
    channel = str(raw_msg.get("channel", "general"))
    author = str(raw_msg.get("author", "Thành viên"))
    mtime = str(raw_msg.get("timestamp") or raw_msg.get("created_at") or raw_msg.get("time") or now_local().isoformat())
    mtype = str(raw_msg.get("type", "message"))

    links = raw_msg.get("links", []) or []
    attachments = raw_msg.get("attachments", []) or []

    is_deadline = mtype == "deadline" or any(k in content.lower() for k in ("deadline", "hạn nộp", "nộp bài", "cổng nộp", "submit"))

    if is_deadline:
        header = "⏰ [HẠN NỘP BÀI / DEADLINE MỚI]"
    else:
        header = "📢 [THÔNG BÁO MỚI TỪ KHÓA HỌC]"

    lines = [
        f"{header}",
        f"📌 Kênh: #{channel}",
        f"👤 Người gửi: {author}",
        f"🕒 Xuất hiện lúc: {mtime[:19].replace('T', ' ')}",
        "",
        f"📝 Nội dung:\n{content[:600]}"
    ]

    if links:
        link_urls = [l.get("url") for l in links if isinstance(l, dict) and l.get("url")]
        if link_urls:
            lines.append(f"\n🔗 Liên kết: {link_urls[0]}")

    if attachments:
        att_names = [a.get("name") for a in attachments if isinstance(a, dict) and a.get("name")]
        if att_names:
            lines.append(f"📎 Tệp đính kèm: {', '.join(att_names)}")

    lines.append("\n🌐 Xem trên Dashboard: http://localhost:8000")
    
    send_telegram_notification("\n".join(lines))



class TelegramBotListener:
    """Polls Telegram getUpdates to handle user commands & Q&A chatbot interactions."""

    def __init__(self) -> None:
        self.token, self.env_chat_id = _get_token_and_chat_id()
        self.last_update_id = 0

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def _api_call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Dict[str, Any]:
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        if params:
            encoded_params = urllib.parse.urlencode(params)
            url += f"?{encoded_params}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def handle_message(self, text: str, chat_id: str, sender_name: str) -> None:
        _save_subscriber(chat_id)
        cmd = text.strip().lower()

        if cmd in ("/start", "/help", "xin chào", "hello", "hi"):
            reply = (
                f"👋 Chào {sender_name}! Mình là Trợ lý AI Khóa học.\n\n"
                f"Các lệnh hỗ trợ:\n"
                f"• /deadlines — Xem danh sách hạn nộp & nhắc nhở gấp\n"
                f"• /labs — Xem danh sách các bài Lab trên GitHub VinUni-AI20k\n"
                f"• /latest — Xem deadline gần nhất sắp đến hạn\n"
                f"• /time — Lấy mốc thời gian hiện tại\n"
                f"• Hoặc gõ bất kỳ câu hỏi nào (ví dụ: 'Hướng dẫn lab ReAct là gì?', 'Khi nào nộp bài?') để Chatbot AI trả lời ngay!"
            )
            send_telegram_notification(reply, chat_id=chat_id)
            return

        if cmd in ("/labs", "/lab", "labs", "danh sách lab", "bài lab"):
            from agents import GitHubLabsAgent
            labs_data = GitHubLabsAgent().list_available_labs()
            labs = labs_data.get("labs", [])
            lines = [f"📚 DANH SÁCH BÀI LAB CÓ SẴN (GITHUB VinUni-AI20k - {len(labs)} REPOS):\n"]
            for l in labs[:10]:
                lines.append(f"• {l.get('name')}\n  🔗 {l.get('url')}\n")
            reply = "\n".join(lines)
            send_telegram_notification(reply, chat_id=chat_id)
            return


        if cmd in ("/deadlines", "/han", "deadlines", "hạn nộp"):
            structured = get_structured()
            reminders_data = DeadlineReminderAgent(structured).make_reminders(72)
            reminders = reminders_data.get("reminders", [])
            if not reminders:
                reply = "🎉 Hiện tại không có deadline nào gấp trong 72 giờ tới!"
            else:
                lines = ["📋 DANH SÁCH DEADLINE & NHẮC NHỞ GẤP (72H):"]
                for r in reminders:
                    lines.append(f"• {r.get('message')}")
                reply = "\n".join(lines)
            send_telegram_notification(reply, chat_id=chat_id)
            return

        if cmd in ("/latest", "/mới nhất", "latest"):
            structured = get_structured()
            latest = DeadlineReminderAgent(structured).latest_deadline()
            reply = latest.get("message") or "Không tìm thấy deadline gần nhất."
            send_telegram_notification(reply, chat_id=chat_id)
            return

        if cmd == "/time":
            structured = get_structured()
            current_time = DeadlineReminderAgent(structured).get_current_time()
            reply = f"🕒 Thời gian hiện tại (Asia/Saigon): {current_time.get('now_iso')}"
            send_telegram_notification(reply, chat_id=chat_id)
            return

        # Default: Route question to AutoToolQAAgent
        structured = get_structured()
        qa_agent = AutoToolQAAgent(structured)
        result = qa_agent.answer(text)
        answer = result.get("answer") or "Xin lỗi, mình chưa tìm thấy thông tin phù hợp."
        reply = f"🤖 AI Trả lời:\n{answer}"
        send_telegram_notification(reply, chat_id=chat_id)

    def run(self) -> None:
        if not self.enabled:
            print("[Telegram] Missing TELEGRAM_BOT_TOKEN in repository-root .env.")
            return

        print(f"[Telegram Bot] Listener started. Polling updates for bot...")
        while True:
            try:
                updates = self._api_call("getUpdates", {"offset": self.last_update_id + 1, "timeout": 10}, timeout=15)
                for update in updates.get("result", []):
                    self.last_update_id = max(self.last_update_id, update.get("update_id", 0))
                    message = update.get("message") or update.get("edited_message")
                    if not message:
                        continue
                    text = message.get("text", "").strip()
                    chat_id = str(message.get("chat", {}).get("id", ""))
                    sender = message.get("from", {})
                    sender_name = sender.get("first_name") or sender.get("username") or "Học viên"

                    if text and chat_id:
                        print(f"[Telegram] Received from {sender_name} ({chat_id}): '{text}'")
                        self.handle_message(text, chat_id, sender_name)
            except Exception as exc:
                time.sleep(3)


def main() -> None:
    bot = TelegramBotListener()
    bot.run()


if __name__ == "__main__":
    main()
