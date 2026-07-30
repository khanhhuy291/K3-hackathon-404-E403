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

import agents
import discord_ingestion


class DiscordIngestionTests(unittest.TestCase):
    def test_message_conversion_keeps_permalink_attachments_and_embeds(self) -> None:
        message = SimpleNamespace(
            id=42,
            content="",
            created_at=datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
            edited_at=None,
            jump_url="https://discord.com/channels/1/2/42",
            guild=SimpleNamespace(name="Course", id=1),
            channel=SimpleNamespace(name="announcements", id=2),
            author=SimpleNamespace(display_name="TA", name="ta", id=3, bot=False),
            attachments=[SimpleNamespace(filename="brief.pdf", url="https://cdn.test/brief.pdf", content_type="application/pdf")],
            embeds=[SimpleNamespace(title="Thông báo", description="Hạn nộp bài lúc 23h59 ngày 01/08", url=None, fields=[])],
            reference=None,
        )
        raw = discord_ingestion.message_to_raw(message)
        self.assertEqual(raw["source_url"], message.jump_url)
        self.assertEqual(raw["attachments"][0]["name"], "brief.pdf")
        self.assertIn("Hạn nộp bài", raw["content"])
        self.assertEqual(raw["type"], "deadline")
        self.assertTrue(discord_ingestion.is_relevant_course_message(raw))

    def test_vietnamese_relevance_and_deadline_format_are_supported(self) -> None:
        raw = {"id": "1", "role": "member", "channel": "thong-bao", "content": "Thông báo: nộp bài lúc 23h59 ngày 01/08"}
        self.assertTrue(discord_ingestion.is_relevant_course_message(raw))
        parsed = agents.RawJsonExtractorAgent(agents.NvidiaOpenAIClient())._deadline_from_text(raw["content"], "2026-07-01T00:00:00+07:00")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.strftime("%Y-%m-%d %H:%M"), "2026-08-01 23:59")

    def test_relevance_rejects_bot_and_ordinary_chatter(self) -> None:
        self.assertFalse(discord_ingestion.is_relevant_course_message({"role": "bot", "content": "deadline"}))
        self.assertFalse(discord_ingestion.is_relevant_course_message({"role": "member", "content": "ăn trưa chưa?", "channel": "general"}))

    def test_ingestion_upserts_then_removes_by_message_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_path = Path(directory) / "live.json"
            status_path = Path(directory) / "status.json"
            message = {"id": "99", "server": "Course", "channel": "announcements", "content": "Deadline nộp bài", "role": "member"}
            updated = {**message, "content": "Deadline nộp bài lúc 23h59 ngày 01/08"}
            with patch.object(discord_ingestion, "RUNTIME_DATA_FILE", runtime_path), patch.object(
                discord_ingestion, "RUNTIME_STATUS_FILE", status_path
            ), patch.object(discord_ingestion, "get_structured", return_value={"stats": {"messages": 1}}):
                first = discord_ingestion.ingest_raw_message(message)
                second = discord_ingestion.ingest_raw_message(message)
                third = discord_ingestion.ingest_raw_message(updated)
                removed = discord_ingestion.remove_raw_message("99")
            self.assertEqual(first["action"], "created")
            self.assertEqual(second["reason"], "duplicate")
            self.assertEqual(third["action"], "updated")
            self.assertTrue(removed["removed"])
            self.assertEqual(json.loads(runtime_path.read_text(encoding="utf-8"))["messages"], [])

    def test_runtime_cache_rebuilds_when_raw_messages_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture.json"
            runtime = root / "runtime.json"
            structured = root / "structured.json"
            runtime_structured = root / "runtime-structured.json"
            copy = root / "copy.json"
            fixture.write_text(json.dumps({"server": "Fixture", "messages": [{"id": "fixture", "content": "hello"}]}), encoding="utf-8")
            runtime.write_text(json.dumps({"server": "Live", "messages": [{"id": "live", "content": "Thông báo"}]}), encoding="utf-8")
            with patch.object(agents, "DATA_FILE", fixture), patch.object(agents, "RUNTIME_DATA_FILE", runtime), patch.object(
                agents, "STRUCTURED_FILE", structured
            ), patch.object(agents, "RUNTIME_STRUCTURED_FILE", runtime_structured), patch.object(agents, "COPY_STRUCTURED_FILE", copy):
                first = agents.get_structured(refresh=True)
                runtime.write_text(json.dumps({"server": "Live", "messages": [{"id": "live", "content": "Thông báo"}, {"id": "next", "content": "Deadline nộp bài"}]}), encoding="utf-8")
                second = agents.get_structured()
            self.assertEqual(first["stats"]["messages"], 2)
            self.assertEqual(second["stats"]["messages"], 3)


if __name__ == "__main__":
    unittest.main()
