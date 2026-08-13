from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from nexoria.checks import require
from nexoria.database import Database


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.messages: dict[tuple[int, int], deque[float]] = defaultdict(deque)

    @property
    def db(self) -> Database:
        return self.bot.database  # type: ignore[attr-defined]

    async def configured_channel(
        self, guild: discord.Guild, key: str
    ) -> discord.TextChannel | None:
        channel_id = await self.db.get(guild.id, f"channel.{key}")
        channel = guild.get_channel(channel_id) if channel_id else None
        return channel if isinstance(channel, discord.TextChannel) else None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        channel = await self.configured_channel(member.guild, "welcome")
        if channel:
            await channel.send(
                embed=discord.Embed(
                    title="👋 Willkommen!",
                    description=f"{member.mention}, willkommen auf **{member.guild.name}**!",
                    color=discord.Color.green(),
                )
            )
        await self.log(member.guild, f"➕ Beitritt: {member} ({member.id})")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        channel = await self.configured_channel(member.guild, "leave")
        if channel:
            await channel.send(
                embed=discord.Embed(
                    title="👋 Auf Wiedersehen",
                    description=f"**{member}** hat den Server verlassen.",
                    color=discord.Color.red(),
                )
            )
        await self.log(member.guild, f"➖ Austritt: {member} ({member.id})")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild and not message.author.bot:
            await self.log(
                message.guild,
                f"🗑️ Gelöscht in {message.channel.mention} von {message.author}: "
                f"{message.clean_content[:1500]}",
            )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild and not before.author.bot and before.content != after.content:
            await self.log(
                before.guild,
                f"✏️ Bearbeitet in {before.channel.mention} von {before.author}\n"
                f"Vorher: {before.clean_content[:700]}\nNachher: {after.clean_content[:700]}",
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if (
            not message.guild
            or message.author.bot
            or not isinstance(message.author, discord.Member)
        ):
            return
        if message.author.guild_permissions.manage_messages:
            return
        now = time.monotonic()
        bucket = self.messages[(message.guild.id, message.author.id)]
        bucket.append(now)
        while bucket and bucket[0] < now - 8:
            bucket.popleft()
        if len(bucket) >= 7:
            bucket.clear()
            try:
                await message.author.timeout(discord.utils.utcnow() + timedelta(seconds=30))
            except (discord.Forbidden, discord.HTTPException, AttributeError):
                pass
            try:
                await message.channel.send(
                    f"{message.author.mention}, bitte nicht spammen.", delete_after=8
                )
            except discord.HTTPException:
                pass

    async def log(self, guild: discord.Guild, text: str) -> None:
        channel = await self.configured_channel(guild, "logs")
        if channel:
            try:
                await channel.send(text, allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                pass

    @app_commands.command(name="rules", description="Postet ein Regelwerk in einen Kanal.")
    async def rules(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        rules_text: str,
    ) -> None:
        if not interaction.guild or not await require(interaction, self.db, "configure"):
            return
        await channel.send(
            embed=discord.Embed(
                title=title[:256], description=rules_text[:4000], color=discord.Color.blurple()
            )
        )
        await interaction.response.send_message("Regelwerk veröffentlicht.", ephemeral=True)

    @app_commands.command(name="security", description="Zeigt den Anti-Spam-Status.")
    async def security(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Anti-Spam aktiv: 7 Nachrichten in 8 Sekunden → 30 Sekunden Timeout.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
