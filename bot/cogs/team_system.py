from __future__ import annotations

import hashlib

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.config import settings
from bot.services import TEAM_LEVELS, highest_team_level, require_permission

DEFAULT_TEAM_ROLES = {
    "Owner": settings.OWNER_ROLE_ID,
    "Co-Owner": settings.CO_OWNER_ROLE_ID,
    "Admin": settings.ADMIN_ROLE_ID,
    "Head Developer": settings.HEAD_DEVELOPER_ROLE_ID,
    "Developer": settings.DEVELOPER_TEAM_ROLE_ID,
    "Test Developer": settings.TEST_DEVELOPER_ROLE_ID,
    "Moderator+": settings.MODERATOR_PLUS_ROLE_ID,
    "Moderator": settings.MODERATOR_ROLE_ID,
    "Supporter": settings.SUPPORTER_ROLE_ID,
    "Test Supporter": settings.TEST_SUPPORTER_TEAM_ROLE_ID,
}


class TeamMemberSelect(discord.ui.UserSelect):
    def __init__(self, mode: str) -> None:
        super().__init__(
            placeholder="Teammitglied auswählen",
            min_values=1,
            max_values=1,
            custom_id=f"nexoria:team:{mode}:member",
        )
        self.mode = mode

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        database = interaction.client.db
        if not await require_permission(interaction, database, "team_stats"):
            return
        member = self.values[0]
        if self.mode == "stats":
            rows = await database.fetchall(
                "SELECT action,COUNT(*) amount FROM moderation_actions "
                "WHERE guild_id=? AND moderator_id=? GROUP BY action ORDER BY action",
                (interaction.guild.id, member.id),
            )
            description = (
                "\n".join(f"**{row['action']}:** {row['amount']}" for row in rows)
                or "Noch keine Moderationsaktionen."
            )
            embed = discord.Embed(
                title=f"📊 Team-Statistik – {member}",
                description=description,
                color=discord.Color.blurple(),
            )
        else:
            rows = await database.fetchall(
                "SELECT user_id,action,reason,duration_seconds,created_at "
                "FROM moderation_actions WHERE guild_id=? AND moderator_id=? "
                "ORDER BY id DESC LIMIT 25",
                (interaction.guild.id, member.id),
            )
            description = (
                "\n".join(
                    f"{row['created_at']} <@{row['user_id']}> – **{row['action']}** "
                    f"– {row['reason']}"
                    for row in rows
                )
                or "Noch kein Verlauf."
            )
            embed = discord.Embed(
                title=f"📋 Verlauf – {member}",
                description=description[:4000],
                color=discord.Color.blurple(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class TeamMemberView(discord.ui.View):
    def __init__(self, mode: str) -> None:
        super().__init__(timeout=300)
        self.add_item(TeamMemberSelect(mode))


class TeamPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Team-Statistiken",
        emoji="📊",
        style=discord.ButtonStyle.primary,
        custom_id="nexoria:team:stats",
    )
    async def stats(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Teammitglied auswählen:", view=TeamMemberView("stats"), ephemeral=True
        )

    @discord.ui.button(
        label="Vollständiger Verlauf",
        emoji="📋",
        style=discord.ButtonStyle.secondary,
        custom_id="nexoria:team:history",
    )
    async def history(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Teammitglied auswählen:", view=TeamMemberView("history"), ephemeral=True
        )


class TeamSystem(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._refresh_locks: set[int] = set()

    async def cog_load(self) -> None:
        self.bot.add_view(TeamPanelView())
        self.refresh_loop.start()

    def cog_unload(self) -> None:
        self.refresh_loop.cancel()

    async def ensure_default_roles(self, guild_id: int) -> None:
        configured = await self.bot.db.role_map(guild_id, "team.")
        for level, role_id in DEFAULT_TEAM_ROLES.items():
            if level not in configured and role_id:
                await self.bot.db.replace_roles(guild_id, f"team.{level}", [role_id])

    async def team_embed(self, guild: discord.Guild) -> discord.Embed:
        await self.ensure_default_roles(guild.id)
        configured = await self.bot.db.role_map(guild.id, "team.")
        grouped: dict[str, list[discord.Member]] = {level: [] for level in TEAM_LEVELS}
        for member in guild.members:
            if member.bot:
                continue
            level = highest_team_level({role.id for role in member.roles}, configured)
            if level:
                grouped[level].append(member)
        embed = discord.Embed(
            title="👥 Nexoria Craft – Team",
            description=(
                "Jedes Mitglied wird ausschließlich unter seiner höchsten "
                "konfigurierten Teamrolle angezeigt."
            ),
            color=discord.Color.blurple(),
        )
        for level in TEAM_LEVELS:
            members = sorted(grouped[level], key=lambda item: item.display_name.casefold())
            if members:
                embed.add_field(
                    name=level,
                    value="\n".join(member.mention for member in members)[:1024],
                    inline=False,
                )
        if not embed.fields:
            embed.add_field(
                name="Noch nicht eingerichtet",
                value="Konfiguriere die Teamrollen mit /settings.",
                inline=False,
            )
        return embed

    async def upsert_panel(
        self,
        guild: discord.Guild,
        kind: str,
        channel: discord.TextChannel,
        embed: discord.Embed,
        view: discord.ui.View | None = None,
    ) -> None:
        payload_hash = hashlib.sha256(str(embed.to_dict()).encode()).hexdigest()
        row = await self.bot.db.fetchone(
            "SELECT * FROM panel_messages WHERE guild_id=? AND kind=?",
            (guild.id, kind),
        )
        message = None
        if row:
            old_channel = guild.get_channel(row["channel_id"])
            if isinstance(old_channel, discord.TextChannel):
                try:
                    message = await old_channel.fetch_message(row["message_id"])
                except (discord.NotFound, discord.Forbidden):
                    pass
        if message and row["payload_hash"] == payload_hash:
            return
        if message and message.channel.id == channel.id:
            await message.edit(embed=embed, view=view)
        else:
            message = await channel.send(embed=embed, view=view)
        await self.bot.db.execute(
            "INSERT INTO panel_messages(guild_id,kind,channel_id,message_id,payload_hash) "
            "VALUES(?,?,?,?,?) ON CONFLICT(guild_id,kind) DO UPDATE SET "
            "channel_id=excluded.channel_id,message_id=excluded.message_id,"
            "payload_hash=excluded.payload_hash",
            (guild.id, kind, channel.id, message.id, payload_hash),
        )

    @app_commands.command(
        name="team-list", description="Erstellt die automatisch aktualisierte Teamliste."
    )
    @app_commands.default_permissions(manage_guild=True)
    async def team_list(self, interaction: discord.Interaction, kanal: discord.TextChannel) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "team_manage"
        ):
            return
        await interaction.response.defer(ephemeral=True)
        await self.upsert_panel(
            interaction.guild,
            "team_list",
            kanal,
            await self.team_embed(interaction.guild),
        )
        await interaction.followup.send(
            f"✅ Teamliste in {kanal.mention} eingerichtet.", ephemeral=True
        )

    @app_commands.command(name="team-panel", description="Erstellt das Teamstatistik-Panel.")
    @app_commands.default_permissions(manage_guild=True)
    async def team_panel(
        self, interaction: discord.Interaction, kanal: discord.TextChannel
    ) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "team_manage"
        ):
            return
        embed = discord.Embed(
            title="🛡️ Nexoria Craft – Team-Panel",
            description=(
                "Statistiken und Moderationsverläufe aus gespeicherten Command- und Panelaktionen."
            ),
            color=discord.Color.blurple(),
        )
        await self.upsert_panel(interaction.guild, "team_stats", kanal, embed, TeamPanelView())
        await interaction.response.send_message(
            f"✅ Team-Panel in {kanal.mention} eingerichtet.", ephemeral=True
        )

    async def refresh_guild(self, guild: discord.Guild) -> None:
        if guild.id in self._refresh_locks:
            return
        self._refresh_locks.add(guild.id)
        try:
            row = await self.bot.db.fetchone(
                "SELECT channel_id FROM panel_messages WHERE guild_id=? AND kind='team_list'",
                (guild.id,),
            )
            if not row:
                return
            channel = guild.get_channel(row["channel_id"])
            if isinstance(channel, discord.TextChannel):
                await self.upsert_panel(guild, "team_list", channel, await self.team_embed(guild))
        finally:
            self._refresh_locks.discard(guild.id)

    @tasks.loop(seconds=30)
    async def refresh_loop(self) -> None:
        for guild in self.bot.guilds:
            await self.refresh_guild(guild)

    @refresh_loop.before_loop
    async def before_refresh_loop(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.roles != after.roles:
            await self.refresh_guild(after.guild)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TeamSystem(bot))
