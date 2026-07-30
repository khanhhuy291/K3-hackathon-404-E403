"""Optional live Discord ingestion for the existing course-assistant pipeline.

This module has no Discord SDK dependency. It normalizes Discord messages into the
existing raw schema, persists only ignored runtime records, and refreshes the
retained extraction/search/Q&A pipeline.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from agents import (
    RUNTIME_DATA_FILE,
    RUNTIME_STATUS_FILE,
    atomic_write_json,
    get_structured,
    normalize_text,
)


RELEVANCE_TERMS = tuple(normalize_text(term) for term in (
    "announcement", "deadline", "due", "assignment", "quiz", "workshop",
    "thông báo", "hạn", "nộp bài", "bài tập", "tài liệu", "slide", "lịch học",
    "meeting", "lớp học", "nộp", "submission",
))
DEADLINE_TERMS = tuple(normalize_text(term) for term in (
    "deadline", "due", "assignment", "quiz", "hạn", "nộp bài", "bài tập", "submission",
))
MEETING_TERMS = tuple(normalize_text(term) for term in ("meeting", "workshop", "lịch học", "buổi học", "zoom"))
QUESTION_TERMS = ("?", "ai biết", "cho hỏi", "làm sao", "như nào")
URL_PATTERN = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
_RUNTIME_LOCK = threading.RLock()


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


def _embed_text(embed: Any) -> str:
    fields = _value(embed, "fields", []) or []
    parts = [_value(embed, "title", ""), _value(embed, "description", ""), _value(embed, "url", "")]
    for field in fields:
        parts.extend([_value(field, "name", ""), _value(field, "value", "")])
    return "\n".join(str(part) for part in parts if part)


def _classify(content: str, channel: str, attachments: List[Dict[str, Any]], links: List[Dict[str, Any]]) -> str:
    text = normalize_text(f"{channel} {content}")
    if any(term in text for term in DEADLINE_TERMS):
        return "deadline"
    if any(term in text for term in MEETING_TERMS):
        return "meeting"
    if attachments or links:
        return "document"
    if "?" in content or any(term in text for term in QUESTION_TERMS):
        return "question"
    if any(term in text for term in RELEVANCE_TERMS):
        return "announcement"
    return "message"


def message_to_raw(message: Any) -> Dict[str, Any]:
    """Convert a discord.py Message (or compatible test double) to develop's raw schema."""
    channel = _value(message, "channel")
    guild = _value(message, "guild") or _value(channel, "guild")
    author = _value(message, "author")
    content = str(_value(message, "content", "") or "")
    embed_text = "\n".join(_embed_text(embed) for embed in (_value(message, "embeds", []) or []))
    combined_content = "\n".join(part for part in (content, embed_text) if part)
    attachments = _attachment_rows(_value(message, "attachments", []))
    links = [{"url": url, "type": "link"} for url in URL_PATTERN.findall(combined_content)]
    reference = _value(message, "reference")
    replied_to = _value(reference, "message_id") if reference else None
    channel_name = _value(channel, "name") or "unknown"

    return {
        "id": str(_value(message, "id", "")),
        "server": _value(guild, "name") or "Discord",
        "channel": channel_name,
        "author": _value(author, "display_name") or _value(author, "name") or "unknown",
        "author_id": str(_value(author, "id", "")),
        "role": "bot" if _value(author, "bot", False) else "member",
        "timestamp": _iso_timestamp(_value(message, "created_at")),
        "updated_at": _iso_timestamp(_value(message, "edited_at")),
        "content": combined_content,
        "attachments": attachments,
        "links": links,
        "reply_to": str(replied_to) if replied_to else None,
        "source_url": _value(message, "jump_url"),
        "type": _classify(combined_content, channel_name, attachments, links),
    }


def is_relevant_course_message(raw_message: Mapping[str, Any], *, allow_bot: bool = False) -> bool:
    """Accept relevant course logistics/resources; keep unknown chatter out of runtime data."""
    if not allow_bot and str(raw_message.get("role", "")).casefold() == "bot":
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
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Runtime crawl data is invalid JSON: {path}") from exc
    return data if isinstance(data, dict) else {"messages": []}


def _status() -> Dict[str, Any]:
    try:
        data = _read_runtime_messages()
        return {
            "mode": "runtime" if RUNTIME_DATA_FILE.exists() else "fixture",
            "live_message_count": len(data.get("messages", [])),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except RuntimeError as exc:
        return {"mode": "runtime", "live_message_count": None, "last_error": str(exc), "updated_at": datetime.now(timezone.utc).isoformat()}


def update_status(**changes: Any) -> Dict[str, Any]:
    current: Dict[str, Any] = {}
    if RUNTIME_STATUS_FILE.exists():
        try:
            current = json.loads(RUNTIME_STATUS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {"last_error": "Crawler status file was invalid JSON."}
    current.update(_status())
    current.update(changes)
    atomic_write_json(RUNTIME_STATUS_FILE, current)
    return current


def crawler_status() -> Dict[str, Any]:
    if not RUNTIME_STATUS_FILE.exists():
        return _status()
    try:
        data = json.loads(RUNTIME_STATUS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _status()
    return {**data, **_status()}


def ingest_raw_message(
    raw_message: Mapping[str, Any], *, refresh: bool = True, prefer_llm: bool = False, allow_bot: bool = False
) -> Dict[str, Any]:
    """Upsert one relevant live message and refresh structured runtime output."""
    normalized = dict(raw_message)
    message_id = str(normalized.get("id", "")).strip()
    if not message_id:
        update_status(last_event="rejected", last_reason="missing_message_id")
        return {"accepted": False, "reason": "missing_message_id"}
    if not is_relevant_course_message(normalized, allow_bot=allow_bot):
        update_status(last_event="rejected", last_reason="not_course_relevant", last_message_id=message_id)
        return {"accepted": False, "reason": "not_course_relevant", "id": message_id}

    with _RUNTIME_LOCK:
        data = _read_runtime_messages()
        messages = [row for row in data.get("messages", []) if isinstance(row, dict)]
        existing_index = next((index for index, row in enumerate(messages) if str(row.get("id", "")) == message_id), None)
        action = "created"
        if existing_index is None:
            messages.append(normalized)
        elif messages[existing_index] != normalized:
            messages[existing_index] = normalized
            action = "updated"
        else:
            update_status(last_event="duplicate", last_reason="unchanged", last_message_id=message_id)
            return {"accepted": False, "reason": "duplicate", "id": message_id}
        data["server"] = normalized.get("server") or data.get("server") or "Discord"
        data["messages"] = messages
        atomic_write_json(RUNTIME_DATA_FILE, data)
        structured = get_structured(refresh=refresh, prefer_llm=prefer_llm)
    update_status(last_event=action, last_reason=None, last_message_id=message_id, last_success_at=datetime.now(timezone.utc).isoformat())
    return {"accepted": True, "action": action, "id": message_id, "stats": structured.get("stats", {})}


def remove_raw_message(message_id: Any, *, refresh: bool = True) -> Dict[str, Any]:
    target = str(message_id)
    with _RUNTIME_LOCK:
        data = _read_runtime_messages()
        messages = [row for row in data.get("messages", []) if isinstance(row, dict)]
        filtered = [row for row in messages if str(row.get("id", "")) != target]
        if len(filtered) == len(messages):
            return {"removed": False, "id": target}
        data["messages"] = filtered
        atomic_write_json(RUNTIME_DATA_FILE, data)
        structured = get_structured(refresh=refresh)
    update_status(last_event="deleted", last_reason=None, last_message_id=target, last_success_at=datetime.now(timezone.utc).isoformat())
    return {"removed": True, "id": target, "stats": structured.get("stats", {})}


def ingest_discord_message(
    message: Any, *, refresh: bool = True, prefer_llm: bool = False, allow_bot: bool = False
) -> Dict[str, Any]:
    return ingest_raw_message(message_to_raw(message), refresh=refresh, prefer_llm=prefer_llm, allow_bot=allow_bot)
