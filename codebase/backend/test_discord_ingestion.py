"""Focused checks for optional Discord crawling without discord.py or network access."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import discord_ingestion


class DiscordIngestionTests(unittest.TestCase):
    def test_message_conversion_keeps_permalink_and_attachments(self) -> None:
        message = SimpleNamespace(
            id=42,
            content="Thông báo: nộp bài trước 23:59 https://example.test/brief",
            created_at=datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
            jump_url="https://discord.com/channels/1/2/42",
            guild=SimpleNamespace(name="Course", id=1),
            channel=SimpleNamespace(name="announcements", id=2),
            author=SimpleNamespace(display_name="TA", name="ta", bot=False),
            attachments=[SimpleNamespace(filename="brief.pdf", url="https://cdn.test/brief.pdf", content_type="application/pdf")],
            reference=None,
        )
        raw = discord_ingestion.message_to_raw(message)
        self.assertEqual(raw["source_url"], message.jump_url)
        self.assertEqual(raw["attachments"][0]["name"], "brief.pdf")
        self.assertEqual(raw["links"][0]["url"], "https://example.test/brief")
        self.assertTrue(discord_ingestion.is_relevant_course_message(raw))

    def test_relevance_rejects_bot_and_ordinary_chatter(self) -> None:
        self.assertFalse(discord_ingestion.is_relevant_course_message({"role": "bot", "content": "deadline"}))
        self.assertFalse(discord_ingestion.is_relevant_course_message({"role": "member", "content": "ăn trưa chưa?", "channel": "general"}))

    def test_ingestion_deduplicates_by_message_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_path = Path(directory) / "live.json"
            message = {"id": "99", "server": "Course", "channel": "announcements", "content": "Deadline nộp bài"}
            with patch.object(discord_ingestion, "RUNTIME_DATA_FILE", runtime_path), patch.object(
                discord_ingestion, "get_structured", return_value={"stats": {"messages": 1}}
            ):
                first = discord_ingestion.ingest_raw_message(message)
                second = discord_ingestion.ingest_raw_message(message)
            self.assertTrue(first["accepted"])
            self.assertEqual(second["reason"], "duplicate")
            self.assertEqual(len(json.loads(runtime_path.read_text(encoding="utf-8"))["messages"]), 1)


if __name__ == "__main__":
    unittest.main()
