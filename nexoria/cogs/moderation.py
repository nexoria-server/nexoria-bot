from __future__ import annotations

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from nexoria.checks import require, safe_dm
from nexoria.database import Database


class Moderation(commands.GroupCog, group_name="moderation", group_description="Moderation"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.database  # type: ignore[attr-defined]

    async def record(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        action: str,
        reason: str,
        duration: int | None = None,
    ) -> None:
        assert interaction.guild
        await self.db.execute(
            "INSERT INTO moderation_actions(guild_id,actor_id,target_id,action,reason,"
            "duration_seconds,created_at) VALUES(?,?,?,?,?,?,datetime('now'))",
            (interaction.guild.id, interaction.user.id, member.id, action, reason, duration),
        )
        embed = discord.Embed(
            title=f"Moderation: {action}",
            color=discord.Color.orange(),
            description=(
                f"Du wurdest auf **{interaction.guild.name}** moderiert.\n\nGrund: {reason}"
            ),
        )
        if duration:
            embed.add_field(name="Dauer", value=f"{duration // 60} Minuten")
        delivered = await safe_dm(member, embed=embed)
        await interaction.response.send_message(
            f"{action} für {member.mention} gespeichert. "
            f"DM: {'zugestellt' if delivered else 'nicht zustellbar'}.",
            ephemeral=True,
        )

    async def guard(self, interaction: discord.Interaction, member: discord.Member) -> bool:
        if not interaction.guild or not await require(interaction, self.db, "moderation"):
            return False
        if member == interaction.user or member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "Dieses Mitglied kann ich nicht moderieren.", ephemeral=True
            )
            return False
        return True

    @app_commands.command(
        name="warn", description="Verwarnt ein Mitglied und speichert die Aktion."
    )
    async def warn(
        self, interaction: discord.Interaction, member: discord.Member, reason: str
    ) -> None:
        if await self.guard(interaction, member):
            await self.record(interaction, member, "Warnung", reason)

    @app_commands.command(
        name="timeout", description="Setzt einen Timeout und speichert die Aktion."
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str,
    ) -> None:
        if await self.guard(interaction, member):
            await member.timeout(timedelta(minutes=minutes), reason=reason)
            await self.record(interaction, member, "Timeout", reason, minutes * 60)

    @app_commands.command(name="kick", description="Kickt ein Mitglied und speichert die Aktion.")
    async def kick(
        self, interaction: discord.Interaction, member: discord.Member, reason: str
    ) -> None:
        if await self.guard(interaction, member):
            await self.record(interaction, member, "Kick", reason)
            await member.kick(reason=reason)

    @app_commands.command(name="ban", description="Bannt ein Mitglied und speichert die Aktion.")
    async def ban(
        self, interaction: discord.Interaction, member: discord.Member, reason: str
    ) -> None:
        if await self.guard(interaction, member):
            await self.record(interaction, member, "Ban", reason)
            await member.ban(reason=reason)

    @app_commands.command(
        name="history", description="Zeigt den Moderationsverlauf eines Mitglieds."
    )
    async def history(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if not interaction.guild or not await require(interaction, self.db, "moderation"):
            return
        rows = await self.db.rows(
            "SELECT action,reason,created_at,actor_id FROM moderation_actions "
            "WHERE guild_id=? AND target_id=? ORDER BY id DESC LIMIT 20",
            (interaction.guild.id, member.id),
        )
        text = (
            "\n".join(
                f"{row['created_at']} • {row['action']} • {row['reason']} • <@{row['actor_id']}>"
                for row in rows
            )
            or "Kein Verlauf vorhanden."
        )
        await interaction.response.send_message(
            embed=discord.Embed(title=f"📋 Verlauf – {member}", description=text[:4000]),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
