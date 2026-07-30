"""Optional discord.py listener that feeds the existing develop ingestion pipeline.

Install optional dependencies first: pip install -r codebase/requirements-discord.txt
Set DISCORD_BOT_TOKEN in the repository-root .env and enable Message Content Intent.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Set

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agents import load_dotenv
from discord_ingestion import ingest_discord_message, remove_raw_message, update_status


def _id_set(name: str) -> Set[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return set()
    values = {value.strip() for value in raw.split(",") if value.strip()}
    invalid = [value for value in values if not value.isdigit()]
    if invalid:
        raise ValueError(f"{name} must contain comma-separated numeric Discord IDs.")
    return values


def _config() -> tuple[Set[str], Set[str], Set[str], bool]:
    guild_ids = _id_set("DISCORD_ALLOWED_GUILD_IDS")
    channel_ids = _id_set("DISCORD_ALLOWED_CHANNEL_IDS")
    trusted_bot_ids = _id_set("DISCORD_TRUSTED_BOT_IDS")
    allow_all = os.getenv("DISCORD_ALLOW_ALL", "").strip() == "1"
    if not allow_all and not guild_ids and not channel_ids:
        raise ValueError(
            "Set DISCORD_ALLOWED_GUILD_IDS or DISCORD_ALLOWED_CHANNEL_IDS, or explicitly set DISCORD_ALLOW_ALL=1."
        )
    return guild_ids, channel_ids, trusted_bot_ids, allow_all


def _allowed(message: Any, guild_ids: Set[str], channel_ids: Set[str]) -> bool:
    guild = getattr(message, "guild", None)
    channel = getattr(message, "channel", None)
    if guild is None:
        return False
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

    guild_ids, channel_ids, trusted_bot_ids, allow_all = _config()
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    supported_channels = (discord.TextChannel, discord.Thread)

    @bot.event
    async def on_ready() -> None:
        update_status(
            listener_state="connected",
            bot_user=str(bot.user),
            allowed_guild_ids=sorted(guild_ids),
            allowed_channel_ids=sorted(channel_ids),
            trusted_bot_ids=sorted(trusted_bot_ids),
            allow_all=allow_all,
            last_error=None,
        )
        print(f"Discord crawler connected as {bot.user}.")

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if not isinstance(message.channel, supported_channels) or not _allowed(message, guild_ids, channel_ids):
            return
        is_trusted_bot = message.author.bot and str(message.author.id) in trusted_bot_ids
        if not message.author.bot or is_trusted_bot:
            try:
                outcome = ingest_discord_message(message, allow_bot=is_trusted_bot)
                if outcome["accepted"]:
                    print(f"{outcome['action'].title()} Discord message {outcome['id']}.")
            except Exception as exc:
                update_status(listener_state="connected", last_event="error", last_error=str(exc)[:300])
                print(f"Discord ingestion error: {exc}")
        # Commands must run even when their command text is not relevant for ingestion.
        if not message.author.bot:
            await bot.process_commands(message)

    @bot.event
    async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
        if after.author.bot or not isinstance(after.channel, supported_channels) or not _allowed(after, guild_ids, channel_ids):
            return
        try:
            outcome = ingest_discord_message(after)
            if outcome["accepted"]:
                print(f"Updated Discord message {outcome['id']}.")
        except Exception as exc:
            update_status(listener_state="connected", last_event="error", last_error=str(exc)[:300])

    @bot.event
    async def on_message_delete(message: discord.Message) -> None:
        if not isinstance(message.channel, supported_channels) or not _allowed(message, guild_ids, channel_ids):
            return
        try:
            outcome = remove_raw_message(message.id)
            if outcome["removed"]:
                print(f"Removed Discord message {outcome['id']}.")
        except Exception as exc:
            update_status(listener_state="connected", last_event="error", last_error=str(exc)[:300])

    @bot.command(name="scan_history")
    async def scan_history(ctx: commands.Context[Any], limit: int = 30) -> None:
        """Ingest up to 100 recent relevant messages from this allowed channel."""
        if not isinstance(ctx.channel, supported_channels) or not _allowed(ctx.message, guild_ids, channel_ids):
            return
        limit = max(1, min(int(limit), 100))
        accepted = updated = duplicates = ignored = errors = 0
        async for message in ctx.channel.history(limit=limit):
            if message.author.bot and str(message.author.id) not in trusted_bot_ids:
                continue
            try:
                is_trusted_bot = message.author.bot and str(message.author.id) in trusted_bot_ids
                outcome = ingest_discord_message(message, allow_bot=is_trusted_bot)
                if outcome["accepted"]:
                    accepted += 1
                    updated += outcome.get("action") == "updated"
                elif outcome["reason"] == "duplicate":
                    duplicates += 1
                else:
                    ignored += 1
            except Exception as exc:
                errors += 1
                update_status(listener_state="connected", last_event="error", last_error=str(exc)[:300])
        await ctx.send(
            f"Đã quét {limit} tin: {accepted} lưu ({updated} cập nhật), {duplicates} trùng, {ignored} bỏ qua, {errors} lỗi."
        )

    return bot


def main() -> None:
    env_path = load_dotenv()
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Missing DISCORD_BOT_TOKEN in the repository-root .env. Dashboard/API remains available without the crawler.")
    try:
        bot = create_bot()
    except (RuntimeError, ValueError) as exc:
        update_status(listener_state="configuration_error", last_error=str(exc)[:300], env_file=str(env_path) if env_path else None)
        raise SystemExit(str(exc)) from exc
    update_status(listener_state="starting", env_file=str(env_path) if env_path else None)
    bot.run(token)


if __name__ == "__main__":
    main()
