"""Entry point — wire source → processor → store → delivery."""

from __future__ import annotations

import asyncio
import logging
import sys

from aperture.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_pipeline() -> None:
    """Fetch → process → store. Returns when all entries are saved."""
    from aperture.processor.summarize import process_entry
    from aperture.source.hn import fetch_top_stories
    from aperture.store.json_store import entry_url_exists, save_entry

    logger.info("Fetching top %d stories from HN...", settings.hn_top_n)
    stories = await fetch_top_stories(settings.hn_top_n)
    logger.info("Got %d stories, processing...", len(stories))

    # Process with concurrency limit to respect API rate limits
    sem = asyncio.Semaphore(5)
    saved = 0

    async def process_and_save(entry):
        nonlocal saved
        async with sem:
            # Dedup: skip if already stored today
            if await entry_url_exists(entry.url):
                return

            meta = await process_entry(entry)

            if meta.relevance_score >= settings.relevance_threshold:
                entry_id = await save_entry(entry, meta)
                logger.info(
                    "Saved %s (%.0f%%) %s",
                    entry_id,
                    meta.relevance_score * 100,
                    entry.title[:60],
                )
                saved += 1
            else:
                logger.debug(
                    "Skipped (%.0f%%) %s",
                    meta.relevance_score * 100,
                    entry.title[:60],
                )

    await asyncio.gather(*[process_and_save(s) for s in stories])
    logger.info("Pipeline done. %d entries saved.", saved)


async def run_bot() -> None:
    """Start the Discord bot, post today's digest, then stay alive for button callbacks."""
    from aperture.delivery.discord_bot import bot, post_digest
    from aperture.store.json_store import load_today_entries

    entries = await load_today_entries()

    @bot.event
    async def on_ready():
        logger.info("Discord bot ready as %s", bot.user)
        await post_digest(entries)
        logger.info("Digest posted. Listening for feedback...")

    await bot.start(settings.discord_token)


async def run() -> None:
    """Full pipeline: fetch + process + store, then post to Discord."""
    await run_pipeline()
    await run_bot()


def cli() -> None:
    """CLI entry point."""
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "fetch":
            # Just run the pipeline, no Discord
            asyncio.run(run_pipeline())
            return
        elif cmd == "post":
            # Just post existing entries to Discord
            asyncio.run(run_bot())
            return

    # Default: full pipeline + Discord
    asyncio.run(run())


if __name__ == "__main__":
    cli()
