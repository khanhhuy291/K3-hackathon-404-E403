"""Optional discord.py listener that feeds the existing develop ingestion pipeline.

Install optional dependencies first: pip install -r codebase/requirements-discord.txt
Set DISCORD_BOT_TOKEN and enable Message Content Intent in Discord Developer Portal.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agents import load_dotenv
from discord_ingestion import ingest_discord_message


def _allowed(message: Any) -> bool:
    guild_ids = {value.strip() for value in os.getenv("DISCORD_ALLOWED_GUILD_IDS", "").split(",") if value.strip()}
    channel_ids = {value.strip() for value in os.getenv("DISCORD_ALLOWED_CHANNEL_IDS", "").split(",") if value.strip()}
    guild = getattr(message, "guild", None)
    channel = getattr(message, "channel", None)
    if guild_ids and str(getattr(guild, "id", "")) not in guild_ids:
        return False
    return not channel_ids or str(getattr(channel, "id", "")) in channel_ids


def create_bot() -> Any:
    try:
        import discord
        from discord.ext import commands
    except ImportError as exc:
        raise RuntimeError(
            "discord.py is required for the crawler. Run: pip install -r codebase/requirements-discord.txt"
        ) from exc

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready() -> None:
        print(f"Discord crawler connected as {bot.user}.")

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot or not isinstance(message.channel, discord.TextChannel) or not _allowed(message):
            return
        outcome = ingest_discord_message(message)
        if outcome["accepted"]:
            print(f"Ingested Discord message {outcome['id']}.")
        await bot.process_commands(message)

    @bot.command(name="scan_history")
    async def scan_history(ctx: commands.Context[Any], limit: int = 30) -> None:
        """Ingest up to 100 recent, non-bot messages from the current text channel."""
        if not isinstance(ctx.channel, discord.TextChannel) or not _allowed(ctx.message):
            return
        limit = max(1, min(int(limit), 100))
        accepted = 0
        duplicates = 0
        ignored = 0
        async for message in ctx.channel.history(limit=limit):
            if message.author.bot:
                continue
            outcome = ingest_discord_message(message)
            if outcome["accepted"]:
                accepted += 1
            elif outcome["reason"] == "duplicate":
                duplicates += 1
            else:
                ignored += 1
        await ctx.send(
            f"Đã quét {limit} tin gần nhất: {accepted} mới, {duplicates} trùng, {ignored} không liên quan."
        )

    return bot


def main() -> None:
    load_dotenv()
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Missing DISCORD_BOT_TOKEN. Dashboard/API remains available without the crawler.")
    create_bot().run(token)


if __name__ == "__main__":
    main()
