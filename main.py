import asyncio
import logging
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands

from bot.config import settings
from bot.database import Database


COGS = [
    "bot.cogs.core",
    "bot.cogs.tickets",
    "bot.cogs.moderation",
    "bot.cogs.announcments",
    "bot.cogs.minecraft",
    "bot.cogs.team",
    "bot.cogs.logs",
    "bot.cogs.applications",
    "bot.cogs.giveaways",
    "bot.cogs.security",
    "bot.cogs.welcome",
    "bot.cogs.rules",
    "bot.cogs.invites",
]


def setup_logging() -> None:
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        settings.LOG_DIR / "bot.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            handler,
        ],
    )


class CommunityBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                users=True,
                roles=False,
                replied_user=False,
            ),
        )

        self.db = Database(settings.DB_PATH)

    async def setup_hook(self) -> None:
        await self.db.connect()
        failed: list[str] = []
        for extension in COGS:
            try:
                await self.load_extension(extension)
                logging.info("Loaded %s", extension)
            except Exception:
                failed.append(extension)
                logging.exception("Failed to load %s", extension)

        if failed:
            raise RuntimeError("Folgende Module konnten nicht geladen werden: " + ", ".join(failed))

        if settings.DEV_GUILD_ID:
            guild = discord.Object(
                id=settings.DEV_GUILD_ID
            )

            self.tree.copy_global_to(guild=guild)

            synced = await self.tree.sync(
                guild=guild
            )
        else:
            synced = await self.tree.sync()

        logging.info(
            "Synced %d commands",
            len(synced),
        )

    async def close(self) -> None:
        await self.db.close()
        await super().close()


async def main() -> None:
    setup_logging()

    if (
        not settings.DISCORD_TOKEN or settings.DISCORD_TOKEN.startswith("PASTE_")
    ):
        raise RuntimeError(
            "DISCORD_TOKEN fehlt. "
            "Bitte .env konfigurieren."
        )

    bot = CommunityBot()

    async with bot:
        await bot.start(settings.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
