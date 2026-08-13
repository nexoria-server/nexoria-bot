from __future__ import annotations

import hashlib

import discord
from discord import app_commands
from discord.ext import commands, tasks

from nexoria.checks import require
from nexoria.database import Database
from nexoria.domain import TEAM_HIERARCHY, highest_team_level


class Team(commands.GroupCog, group_name="team", group_description="Team-Verwaltung"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.refresh_panels.start()

    def cog_unload(self) -> None:
        self.refresh_panels.cancel()

    @property
    def db(self) -> Database:
        return self.bot.database  # type: ignore[attr-defined]

    async def team_embed(self, guild: discord.Guild) -> discord.Embed:
        configured = await self.db.configured_roles(guild.id, "team.")
        grouped: dict[str, list[discord.Member]] = {level: [] for level in TEAM_HIERARCHY}
        for member in guild.members:
            level = highest_team_level((role.id for role in member.roles), configured)
            if level:
                grouped[level].append(member)
        embed = discord.Embed(
            title="👥 Nexoria Craft – Team",
            color=discord.Color.blurple(),
            description="Jedes Mitglied erscheint ausschließlich unter seiner höchsten Teamrolle.",
        )
        for level in TEAM_HIERARCHY:
            members = sorted(grouped[level], key=lambda member: member.display_name.casefold())
            if members:
                embed.add_field(
                    name=level,
                    value="\n".join(member.mention for member in members)[:1024],
                    inline=False,
                )
        if not embed.fields:
            embed.description = "Noch keine Teamrollen konfiguriert. Nutze /config."
        return embed

    async def leadership_embed(self, guild: discord.Guild) -> discord.Embed:
        sections = await self.db.rows(
            "SELECT name,description FROM leadership_sections "
            "WHERE guild_id=? AND enabled=1 ORDER BY position",
            (guild.id,),
        )
        embed = discord.Embed(title="👑 Nexoria Craft – Team-Leitung", color=discord.Color.gold())
        for row in sections:
            role_ids = await self.db.roles(guild.id, f"leadership.{row['name']}")
            members = [
                member for member in guild.members if role_ids & {role.id for role in member.roles}
            ]
            value = (
                "\n".join(
                    member.mention
                    for member in sorted(members, key=lambda member: member.display_name.casefold())
                )
                or "Nicht besetzt"
            )
            embed.add_field(name=str(row["name"]), value=value[:1024], inline=False)
        return embed

    async def upsert_panel(
        self, guild: discord.Guild, channel: discord.TextChannel, kind: str, embed: discord.Embed
    ) -> None:
        digest = hashlib.sha256(str(embed.to_dict()).encode()).hexdigest()
        rows = await self.db.rows(
            "SELECT message_id,payload_hash FROM panels WHERE guild_id=? AND kind=?",
            (guild.id, kind),
        )
        message = None
        if rows and rows[0]["message_id"]:
            try:
                message = await channel.fetch_message(rows[0]["message_id"])
            except (discord.NotFound, discord.Forbidden):
                pass
        if message and rows[0]["payload_hash"] == digest:
            return
        if message:
            await message.edit(embed=embed)
        else:
            message = await channel.send(embed=embed)
        await self.db.execute(
            "INSERT INTO panels(guild_id,kind,channel_id,message_id,payload_hash) "
            "VALUES(?,?,?,?,?) "
            "ON CONFLICT(guild_id,kind) DO UPDATE SET channel_id=excluded.channel_id,"
            "message_id=excluded.message_id,payload_hash=excluded.payload_hash",
            (guild.id, kind, channel.id, message.id, digest),
        )

    @app_commands.command(name="panel", description="Erstellt oder verschiebt die Team-Liste.")
    async def panel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.guild or not await require(interaction, self.db, "team.manage"):
            return
        await self.upsert_panel(
            interaction.guild, channel, "team", await self.team_embed(interaction.guild)
        )
        await interaction.response.send_message(
            f"Team-Liste in {channel.mention} aktualisiert.", ephemeral=True
        )

    @app_commands.command(name="stats", description="Zeigt Moderationsstatistiken des Teams.")
    async def stats(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        if not interaction.guild or not await require(interaction, self.db, "leadership.view"):
            return
        member = member or interaction.user  # type: ignore[assignment]
        rows = await self.db.rows(
            "SELECT action,COUNT(*) count FROM moderation_actions "
            "WHERE guild_id=? AND actor_id=? GROUP BY action",
            (interaction.guild.id, member.id),
        )
        details = (
            "\n".join(f"{row['action']}: **{row['count']}**" for row in rows) or "Keine Aktionen"
        )
        await interaction.response.send_message(
            embed=discord.Embed(title=f"📊 Statistik – {member}", description=details),
            ephemeral=True,
        )

    @app_commands.command(name="refresh", description="Aktualisiert Team-Panels sofort.")
    async def refresh(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not await require(interaction, self.db, "team.manage"):
            return
        await interaction.response.defer(ephemeral=True)
        await self.refresh_guild(interaction.guild)
        await interaction.followup.send("Panels aktualisiert.", ephemeral=True)

    async def refresh_guild(self, guild: discord.Guild) -> None:
        for kind in ("team", "leadership"):
            rows = await self.db.rows(
                "SELECT channel_id FROM panels WHERE guild_id=? AND kind=?", (guild.id, kind)
            )
            if not rows:
                continue
            channel = guild.get_channel(rows[0]["channel_id"])
            if not isinstance(channel, discord.TextChannel):
                continue
            embed = await (
                self.team_embed(guild) if kind == "team" else self.leadership_embed(guild)
            )
            await self.upsert_panel(guild, channel, kind, embed)

    @tasks.loop(seconds=30)
    async def refresh_panels(self) -> None:
        for guild in self.bot.guilds:
            await self.refresh_guild(guild)

    @refresh_panels.before_loop
    async def before_refresh(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.roles != after.roles:
            await self.refresh_guild(after.guild)


class Leadership(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="team-leitungs-panel", description="Erstellt das Verantwortungs-Panel."
    )
    async def panel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        db: Database = self.bot.database  # type: ignore[attr-defined]
        if not interaction.guild or not await require(interaction, db, "leadership.manage"):
            return
        team = self.bot.get_cog("Team")
        if not isinstance(team, Team):
            await interaction.response.send_message("Team-Modul nicht verfügbar.", ephemeral=True)
            return
        await team.upsert_panel(
            interaction.guild, channel, "leadership", await team.leadership_embed(interaction.guild)
        )
        await interaction.response.send_message(
            f"Team-Leitungs-Panel in {channel.mention} aktualisiert.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Team(bot))
    await bot.add_cog(Leadership(bot))
