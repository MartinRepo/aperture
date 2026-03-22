"""Discord bot — posts digests and handles feedback buttons."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from aperture.config import settings
from aperture.models import EntryMeta, FeedbackRecord, RawEntry
from aperture.store import json_store as store

logger = logging.getLogger(__name__)

# Minimal intents — we only need to send messages and handle interactions
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ── Relevance indicator ──────────────────────────────────────────────────────

def _relevance_dot(score: float) -> str:
    if score >= 0.8:
        return "\U0001f534"  # red circle — high
    if score >= 0.6:
        return "\U0001f7e1"  # yellow circle — medium
    return "\u26aa"          # white circle — low


def _format_tags(tags: list[str]) -> str:
    return " ".join(f"`{t}`" for t in tags[:5])


# ── Feedback buttons ─────────────────────────────────────────────────────────

class FeedbackView(discord.ui.View):
    """Persistent view with Useful / Not Useful / Wrong buttons."""

    def __init__(self, entry_id: str):
        # timeout=None makes buttons work even after bot restarts
        super().__init__(timeout=None)
        self.entry_id = entry_id

    async def _record(
        self, interaction: discord.Interaction, action: str
    ) -> None:
        record = FeedbackRecord(
            entry_id=self.entry_id,
            action=action,  # type: ignore[arg-type]
            timestamp=datetime.now(timezone.utc),
        )
        await store.append_feedback(record)

        # Disable all buttons after one click
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(view=self)
        logger.info("Feedback: %s on %s", action, self.entry_id)

    @discord.ui.button(label="Useful", style=discord.ButtonStyle.green, custom_id="useful")
    async def useful(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._record(interaction, "useful")

    @discord.ui.button(label="Not Useful", style=discord.ButtonStyle.grey, custom_id="not_useful")
    async def not_useful(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._record(interaction, "not_useful")

    @discord.ui.button(label="Wrong", style=discord.ButtonStyle.red, custom_id="wrong")
    async def wrong(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._record(interaction, "wrong")


# ── Digest posting ───────────────────────────────────────────────────────────

def _build_embed(
    entry_id: str, entry: RawEntry, meta: EntryMeta
) -> discord.Embed:
    dot = _relevance_dot(meta.relevance_score)
    tags_str = _format_tags(meta.tags)

    embed = discord.Embed(
        title=f"{dot} {entry.title}",
        url=entry.url,
        description=meta.llm_summary,
        color=0x5865F2,
        timestamp=entry.timestamp,
    )
    embed.add_field(name="Tags", value=tags_str, inline=True)
    embed.add_field(
        name="Relevance",
        value=f"{meta.relevance_score:.0%}",
        inline=True,
    )
    embed.set_footer(text=f"{entry.source} • {entry_id}")
    return embed


async def post_digest(
    entries: list[tuple[str, RawEntry, EntryMeta]],
) -> None:
    """Post today's digest to the configured Discord channel."""
    channel = bot.get_channel(settings.discord_channel_id)
    if channel is None:
        logger.error(
            "Channel %d not found. Is the bot in the server?",
            settings.discord_channel_id,
        )
        return

    if not entries:
        await channel.send("No relevant entries found today.")  # type: ignore[union-attr]
        return

    # Sort by relevance, highest first
    entries_sorted = sorted(entries, key=lambda x: x[2].relevance_score, reverse=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await channel.send(f"**Daily Digest — {today}** ({len(entries_sorted)} entries)")  # type: ignore[union-attr]

    for entry_id, entry, meta in entries_sorted:
        embed = _build_embed(entry_id, entry, meta)
        # Each entry needs its own FeedbackView with unique custom_ids
        view = FeedbackView(entry_id)
        # Override custom_ids to be unique per entry
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.custom_id = f"{child.custom_id}:{entry_id}"
        await channel.send(embed=embed, view=view)  # type: ignore[union-attr]


def create_bot() -> commands.Bot:
    """Return the configured bot instance."""
    return bot
