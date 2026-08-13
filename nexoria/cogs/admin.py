from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from nexoria.database import Database
from nexoria.domain import TEAM_HIERARCHY

PURPOSES = {
    "Teamstufe": [f"team.{name}" for name in TEAM_HIERARCHY],
    "Berechtigung": [
        "permission.configure",
        "permission.team.manage",
        "permission.moderation",
        "permission.tickets",
        "permission.applications",
        "permission.minecraft",
        "permission.giveaways",
        "permission.announcements",
        "permission.leadership.view",
        "permission.leadership.manage",
        "permission.archives",
    ],
    "Systemrolle": [
        "ticket.staff",
        "application.staff",
        "application.Test Supporter.accepted",
        "application.Test Developer.accepted",
        "application.Media.accepted",
        "application.Partner.accepted",
        "leadership.Team-Leitung",
        "leadership.Mentoren",
        "leadership.Developer-Leitung",
        "leadership.Builder-Leitung",
        "leadership.Media-Leitung",
        "leadership.Partner-Leitung",
    ],
}


class PurposeSelect(discord.ui.Select):
    def __init__(self, category: str) -> None:
        options = [
            discord.SelectOption(label=value[:100], value=value) for value in PURPOSES[category]
        ]
        super().__init__(placeholder="Zweck auswählen", options=options[:25])

    async def callback(self, interaction: discord.Interaction) -> None:
        purpose = self.values[0]
        await interaction.response.send_message(
            f"Rollen für {purpose} auswählen:", view=RoleConfigView(purpose), ephemeral=True
        )


class PurposeView(discord.ui.View):
    def __init__(self, category: str) -> None:
        super().__init__(timeout=180)
        self.add_item(PurposeSelect(category))


class RolePicker(discord.ui.RoleSelect):
    def __init__(self, purpose: str) -> None:
        super().__init__(placeholder="Eine oder mehrere Rollen", min_values=0, max_values=25)
        self.purpose = purpose

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        db: Database = interaction.client.database  # type: ignore[attr-defined]
        await db.replace_roles(
            interaction.guild.id, self.purpose, [role.id for role in self.values]
        )
        await interaction.response.send_message(
            f"{self.purpose} wurde mit {len(self.values)} Rolle(n) gespeichert.", ephemeral=True
        )


class RoleConfigView(discord.ui.View):
    def __init__(self, purpose: str) -> None:
        super().__init__(timeout=180)
        self.add_item(RolePicker(purpose))


class ConfigPanel(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=300)

    @discord.ui.button(label="Teamrollen", emoji="👥", style=discord.ButtonStyle.primary)
    async def team(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Teamstufe wählen:", view=PurposeView("Teamstufe"), ephemeral=True
        )

    @discord.ui.button(label="Berechtigungen", emoji="🔐", style=discord.ButtonStyle.primary)
    async def permissions(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Berechtigung wählen:", view=PurposeView("Berechtigung"), ephemeral=True
        )

    @discord.ui.button(label="Systemrollen", emoji="⚙️", style=discord.ButtonStyle.secondary)
    async def systems(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Systemzweck wählen:", view=PurposeView("Systemrolle"), ephemeral=True
        )


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="config", description="Öffnet das zentrale Konfigurationspanel.")
    @app_commands.default_permissions(manage_guild=True)
    async def config(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Nur auf einem Server verfügbar.", ephemeral=True
            )
            return
        db: Database = self.bot.database  # type: ignore[attr-defined]
        roles = await db.roles(interaction.guild.id, "permission.configure")
        has_role = bool(roles & {role.id for role in interaction.user.roles})
        if not interaction.user.guild_permissions.administrator and not has_role:
            await interaction.response.send_message(
                "Du hast keine Berechtigung für diese Aktion.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="⚙️ Nexoria Administration",
            description="Konfiguriere Rollen und serverseitig geprüfte Berechtigungen pro Guild.",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, view=ConfigPanel(), ephemeral=True)

    @app_commands.command(
        name="commands", description="Zeigt alle verfügbaren Commands automatisch an."
    )
    async def commands_panel(self, interaction: discord.Interaction) -> None:
        lines = []
        for command in sorted(self.bot.tree.walk_commands(), key=lambda item: item.qualified_name):
            params = " ".join(f"<{parameter.name}>" for parameter in command.parameters)
            lines.append(
                f"/{command.qualified_name} {params}\n{command.description or 'Keine Beschreibung'}"
            )
        page = lines[:10]
        embed = discord.Embed(
            title="🤖 Commands", description="\n\n".join(page), color=discord.Color.blurple()
        )
        embed.set_footer(text=f"{len(lines)} Commands • automatisch erkannt")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="config-channel", description="Speichert einen Systemkanal pro Guild."
    )
    @app_commands.choices(
        purpose=[
            app_commands.Choice(name="Ticket-Archiv", value="ticket_archive"),
            app_commands.Choice(name="Bewerbungsprüfung", value="application_review"),
            app_commands.Choice(name="Willkommen", value="welcome"),
            app_commands.Choice(name="Verabschiedung", value="leave"),
            app_commands.Choice(name="Logs", value="logs"),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def config_channel(
        self,
        interaction: discord.Interaction,
        purpose: app_commands.Choice[str],
        channel: discord.TextChannel,
    ) -> None:
        if not interaction.guild:
            return
        db: Database = self.bot.database  # type: ignore[attr-defined]
        await db.set(interaction.guild.id, f"channel.{purpose.value}", channel.id)
        await interaction.response.send_message(
            f"{purpose.name}: {channel.mention} gespeichert.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
