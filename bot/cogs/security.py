from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils import send_log


class Security(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.history: dict[tuple[int, int], deque[tuple[float, str]]] = defaultdict(
            lambda: deque(maxlen=12)
        )
        self.joins: dict[int, deque[float]] = defaultdict(deque)
        self.window = 8
        self.limit = 6
        self.mention_limit = 5
        self.duplicate_limit = 3
        self.timeout_minutes = 10
        self._raid_alerted_at: dict[int, float] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if (
            not message.guild
            or message.author.bot
            or not isinstance(message.author, discord.Member)
            or message.author.guild_permissions.manage_messages
        ):
            return
        now = time.monotonic()
        key = (message.guild.id, message.author.id)
        bucket = self.history[key]
        text = message.content.strip().casefold()
        bucket.append((now, text))
        while bucket and now - bucket[0][0] > self.window:
            bucket.popleft()
        mentions = (
            len(message.mentions)
            + len(message.role_mentions)
            + int(message.mention_everyone)
        )
        duplicates = sum(1 for _, value in bucket if value and value == text)
        reason = None
        if len(bucket) >= self.limit:
            reason = "Nachrichten-Spam"
        elif mentions >= self.mention_limit:
            reason = "Mention-Spam"
        elif duplicates >= self.duplicate_limit:
            reason = "Wiederholte Nachrichten"
        if not reason:
            return
        try:
            await message.delete()
            await message.author.timeout(
                timedelta(minutes=self.timeout_minutes), reason=f"Anti-Spam: {reason}"
            )
        except (discord.Forbidden, discord.HTTPException):
            pass
        await send_log(
            self.bot,
            message.guild,
            "🚫 Anti-Spam",
            f"{message.author.mention}: {reason}, Timeout {self.timeout_minutes} Min.",
            discord.Color.red(),
        )
        bucket.clear()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        bucket = self.joins[member.guild.id]
        now = time.monotonic()
        bucket.append(now)
        while bucket and now - bucket[0] > 20:
            bucket.popleft()
        last_alert = self._raid_alerted_at.get(member.guild.id, 0)
        if len(bucket) >= 10 and now - last_alert > 60:
            self._raid_alerted_at[member.guild.id] = now
            await send_log(
                self.bot,
                member.guild,
                "🚨 Möglicher Join-Raid",
                f"{len(bucket)} Joins in 20 Sekunden.",
                discord.Color.red(),
            )

    @app_commands.command(name="security", description="Zeigt den Anti-Spam-Status.")
    @app_commands.default_permissions(manage_guild=True)
    async def security(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"🚫 Anti-Spam aktiv — {self.limit} Nachrichten/{self.window}s, "
            f"{self.mention_limit} Mentions, {self.timeout_minutes} Min. Timeout.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Security(bot))
