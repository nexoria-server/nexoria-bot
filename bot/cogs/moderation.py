from __future__ import annotations

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import success
from bot.services import require_permission
from bot.utils import send_log


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def guard(self, interaction: discord.Interaction, member: discord.Member) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        if not await require_permission(interaction, self.bot.db, "moderation"):
            return False
        if member == interaction.user:
            await interaction.response.send_message(
                "❌ Du kannst dich nicht selbst moderieren.", ephemeral=True
            )
            return False
        if member == interaction.guild.owner or member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ Dieses Mitglied steht auf derselben oder einer höheren Rollenstufe.",
                ephemeral=True,
            )
            return False
        me = interaction.guild.me
        if me and member.top_role >= me.top_role:
            await interaction.response.send_message(
                "❌ Meine Bot-Rolle steht nicht hoch genug.", ephemeral=True
            )
            return False
        return True

    async def dm(
        self,
        member: discord.Member,
        guild: discord.Guild,
        action: str,
        reason: str,
        duration: str | None = None,
    ) -> bool:
        embed = discord.Embed(
            title=f"Moderation: {action}",
            description=f"Du wurdest auf **{guild.name}** moderiert.\n\n**Grund:** {reason}",
            color=discord.Color.orange(),
        )
        if duration:
            embed.add_field(name="Dauer", value=duration)
        try:
            await member.send(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    async def record(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        action: str,
        reason: str,
        duration_seconds: int | None = None,
    ) -> None:
        assert interaction.guild
        await self.bot.db.execute(
            "INSERT INTO moderation_actions("
            "guild_id,user_id,moderator_id,action,reason,duration_seconds"
            ") VALUES(?,?,?,?,?,?)",
            (
                interaction.guild.id,
                member.id,
                interaction.user.id,
                action,
                reason,
                duration_seconds,
            ),
        )

    @app_commands.command(name="warn", description="Verwarnt ein Mitglied.")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(
        self, interaction: discord.Interaction, member: discord.Member, grund: str
    ) -> None:
        if not await self.guard(interaction, member):
            return
        await self.bot.db.execute(
            "INSERT INTO warnings(guild_id,user_id,moderator_id,reason) VALUES(?,?,?,?)",
            (interaction.guild.id, member.id, interaction.user.id, grund),
        )
        await self.record(interaction, member, "Warnung", grund)
        delivered = await self.dm(member, interaction.guild, "Warnung", grund)
        await interaction.response.send_message(
            embed=success(
                "Warnung",
                f"{member.mention} wurde verwarnt. "
                f"DM: {'zugestellt' if delivered else 'nicht zustellbar'}.",
            )
        )
        await send_log(
            self.bot,
            interaction.guild,
            "⚠️ Warnung",
            f"{member.mention} durch {interaction.user.mention}\n**Grund:** {grund}",
            discord.Color.orange(),
        )

    @app_commands.command(name="warnings", description="Zeigt Warnungen eines Mitglieds.")
    @app_commands.default_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if not await require_permission(interaction, self.bot.db, "moderation"):
            return
        rows = await self.bot.db.fetchall(
            "SELECT reason,moderator_id,created_at FROM warnings "
            "WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 15",
            (interaction.guild.id, member.id),
        )
        if not rows:
            await interaction.response.send_message("Keine Warnungen.", ephemeral=True)
            return
        await interaction.response.send_message(
            "\n".join(
                f"• {row['reason']} — <@{row['moderator_id']}> ({row['created_at']})"
                for row in rows
            ),
            ephemeral=True,
        )

    @app_commands.command(name="timeout", description="Setzt einen Timeout.")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minuten: app_commands.Range[int, 1, 40320],
        grund: str = "Kein Grund angegeben",
    ) -> None:
        if not await self.guard(interaction, member):
            return
        await member.timeout(timedelta(minutes=minuten), reason=grund)
        await self.record(interaction, member, "Timeout", grund, minuten * 60)
        await self.dm(member, interaction.guild, "Timeout", grund, f"{minuten} Minuten")
        await interaction.response.send_message(
            embed=success("Timeout", f"{member.mention}: {minuten} Minuten.")
        )
        await send_log(
            self.bot,
            interaction.guild,
            "⏱️ Timeout",
            f"{member.mention} durch {interaction.user.mention}\n{grund}",
            discord.Color.orange(),
        )

    @app_commands.command(name="kick", description="Kickt ein Mitglied.")
    @app_commands.default_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        grund: str = "Kein Grund angegeben",
    ) -> None:
        if not await self.guard(interaction, member):
            return
        await self.dm(member, interaction.guild, "Kick", grund)
        await self.record(interaction, member, "Kick", grund)
        await member.kick(reason=grund)
        await interaction.response.send_message(embed=success("Kick", f"{member} wurde gekickt."))
        await send_log(
            self.bot,
            interaction.guild,
            "👢 Kick",
            f"{member} durch {interaction.user.mention}\n{grund}",
            discord.Color.red(),
        )

    @app_commands.command(name="ban", description="Bannt ein Mitglied.")
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        grund: str = "Kein Grund angegeben",
    ) -> None:
        if not await self.guard(interaction, member):
            return
        await self.dm(member, interaction.guild, "Ban", grund)
        await self.record(interaction, member, "Ban", grund)
        await member.ban(reason=grund)
        await interaction.response.send_message(embed=success("Ban", f"{member} wurde gebannt."))
        await send_log(
            self.bot,
            interaction.guild,
            "🔨 Ban",
            f"{member} durch {interaction.user.mention}\n{grund}",
            discord.Color.red(),
        )

    @app_commands.command(name="history", description="Zeigt den Moderationsverlauf.")
    @app_commands.default_permissions(moderate_members=True)
    async def history(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if not await require_permission(interaction, self.bot.db, "moderation"):
            return
        rows = await self.bot.db.fetchall(
            "SELECT action,reason,moderator_id,created_at FROM moderation_actions "
            "WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 20",
            (interaction.guild.id, member.id),
        )
        text = (
            "\n".join(
                f"• {row['created_at']} — **{row['action']}** — {row['reason']} "
                f"(<@{row['moderator_id']}>)"
                for row in rows
            )
            or "Kein Verlauf vorhanden."
        )
        await interaction.response.send_message(
            embed=discord.Embed(title=f"📋 Verlauf — {member}", description=text[:4000]),
            ephemeral=True,
        )

    @app_commands.command(name="clear", description="Löscht bis zu 100 Nachrichten.")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(
        self, interaction: discord.Interaction, anzahl: app_commands.Range[int, 1, 100]
    ) -> None:
        if not await require_permission(interaction, self.bot.db, "moderation"):
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ Ungültiger Kanal.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=anzahl)
        await interaction.followup.send(f"🧹 {len(deleted)} Nachrichten gelöscht.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
