from __future__ import annotations

import logging

import discord
from discord.ext import commands

from .database import Database
from .settings import Settings

EXTENSIONS = (
    "nexoria.cogs.admin",
    "nexoria.cogs.team",
    "nexoria.cogs.moderation",
    "nexoria.cogs.operations",
    "nexoria.cogs.events",
)


class NexoriaBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings
        self.database = Database(settings.database_path)

    async def setup_hook(self) -> None:
        await self.database.connect()
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        await self.tree.sync()

    async def close(self) -> None:
        await self.database.close()
        await super().close()

    async def on_ready(self) -> None:
        assert self.user
        logging.getLogger(__name__).info("Angemeldet als %s (%s)", self.user, self.user.id)
        for guild in self.guilds:
            await self.database.ensure_guild(guild.id)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.database.ensure_guild(guild.id)
