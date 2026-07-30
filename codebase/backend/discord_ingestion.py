"""Optional live Discord ingestion for the existing course-assistant pipeline.

This module deliberately stores crawled messages outside tracked fixtures. It has no
Discord SDK dependency so conversion and persistence can be tested locally.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from agents import RUNTIME_DATA_FILE, get_structured, normalize_text


RELEVANCE_TERMS = (
    "announcement", "deadline", "due", "assignment", "quiz", "workshop",
    "thông báo", "hạn", "nộp bài", "bài tập", "tài liệu", "slide", "lịch học",
)
URL_PATTERN = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _iso_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _attachment_rows(attachments: Iterable[Any]) -> List[Dict[str, Any]]:
    rows = []
    for attachment in attachments or []:
        rows.append({
            "name": _value(attachment, "filename") or _value(attachment, "name") or "attachment",
            "url": _value(attachment, "url"),
            "type": _value(attachment, "content_type") or "attachment",
        })
    return rows


def message_to_raw(message: Any) -> Dict[str, Any]:
    """Convert a discord.py Message (or compatible test double) to develop's raw schema."""
    channel = _value(message, "channel")
    guild = _value(message, "guild") or _value(channel, "guild")
    author = _value(message, "author")
    content = str(_value(message, "content", "") or "")
    attachments = _attachment_rows(_value(message, "attachments", []))
    links = [{"url": url, "type": "link"} for url in URL_PATTERN.findall(content)]
    reference = _value(message, "reference")
    replied_to = _value(reference, "message_id") if reference else None

    return {
        "id": str(_value(message, "id", "")),
        "server": _value(guild, "name") or "Discord",
        "channel": _value(channel, "name") or "unknown",
        "author": _value(author, "display_name") or _value(author, "name") or "unknown",
        "role": "bot" if _value(author, "bot", False) else "member",
        "timestamp": _iso_timestamp(_value(message, "created_at")),
        "content": content,
        "attachments": attachments,
        "links": links,
        "reply_to": str(replied_to) if replied_to else None,
        "source_url": _value(message, "jump_url"),
        "type": "message",
    }


def is_relevant_course_message(raw_message: Mapping[str, Any]) -> bool:
    """Keep likely course logistics/resources; do not pretend unclear chat is authoritative."""
    if str(raw_message.get("role", "")).casefold() == "bot":
        return False
    text = normalize_text(" ".join([
        str(raw_message.get("content", "")),
        str(raw_message.get("channel", "")),
        " ".join(str(link.get("url", "")) for link in raw_message.get("links", []) if isinstance(link, Mapping)),
    ]))
    return bool(raw_message.get("attachments")) or any(term in text for term in RELEVANCE_TERMS)


def _read_runtime_messages(path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or RUNTIME_DATA_FILE
    if not path.exists() or path.stat().st_size == 0:
        return {"messages": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"messages": []}
    return data if isinstance(data, dict) else {"messages": []}


def ingest_raw_message(raw_message: Mapping[str, Any], *, refresh: bool = True) -> Dict[str, Any]:
    """Persist one relevant live message exactly once and refresh structured output."""
    normalized = dict(raw_message)
    message_id = str(normalized.get("id", "")).strip()
    if not message_id:
        return {"accepted": False, "reason": "missing_message_id"}
    if not is_relevant_course_message(normalized):
        return {"accepted": False, "reason": "not_course_relevant", "id": message_id}

    data = _read_runtime_messages()
    messages = [row for row in data.get("messages", []) if isinstance(row, dict)]
    if any(str(row.get("id", "")) == message_id for row in messages):
        return {"accepted": False, "reason": "duplicate", "id": message_id}

    messages.append(normalized)
    data["server"] = normalized.get("server") or data.get("server") or "Discord"
    data["messages"] = messages
    RUNTIME_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    structured = get_structured(refresh=refresh)
    return {"accepted": True, "id": message_id, "stats": structured.get("stats", {})}


def ingest_discord_message(message: Any, *, refresh: bool = True) -> Dict[str, Any]:
    return ingest_raw_message(message_to_raw(message), refresh=refresh)
