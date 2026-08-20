from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.services import (
    DEFAULT_APPLICATION_TYPES,
    DEFAULT_TICKET_TYPES,
    TEAM_LEVELS,
    ensure_guild_defaults,
    require_permission,
)

PERMISSIONS = {
    "settings": "System konfigurieren",
    "team_manage": "Team-System verwalten",
    "team_stats": "Team-Statistiken ansehen",
    "moderation": "Moderation ausführen",
    "tickets": "Tickets verwalten",
    "ticket_archive": "Ticketarchiv ansehen",
    "applications": "Bewerbungen bearbeiten",
    "application_archive": "Bewerbungsarchiv ansehen",
    "minecraft_details": "Minecraft-Spielerdetails",
    "giveaways": "Giveaways verwalten",
    "announcements": "Announcements erstellen",
    "mention_everyone": "@everyone/@here verwenden",
}


class PurposeSelect(discord.ui.Select):
    def __init__(self, kind: str) -> None:
        if kind == "team":
            purposes = [(f"team.{level}", level) for level in TEAM_LEVELS]
        elif kind == "permissions":
            purposes = [(f"permission.{key}", label) for key, label in PERMISSIONS.items()]
        elif kind == "tickets":
            purposes = [
                (f"ticket.{key}.staff", f"{value[0]} bearbeiten")
                for key, value in DEFAULT_TICKET_TYPES.items()
            ]
        else:
            purposes = []
            for key, value in DEFAULT_APPLICATION_TYPES.items():
                purposes.extend(
                    [
                        (f"application.{key}.staff", f"{value['name']}: bearbeiten"),
                        (f"application.{key}.accepted", f"{value['name']}: Annahme"),
                        (f"application.{key}.test", f"{value['name']}: Testphase"),
                    ]
                )
        super().__init__(
            placeholder="Bereich auswählen",
            options=[
                discord.SelectOption(label=label[:100], value=purpose)
                for purpose, label in purposes[:25]
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"Rollen für **{self.values[0]}** auswählen:",
            view=RoleBindingView(self.values[0]),
            ephemeral=True,
        )


class PurposeView(discord.ui.View):
    def __init__(self, kind: str) -> None:
        super().__init__(timeout=300)
        self.add_item(PurposeSelect(kind))


class RoleBindingSelect(discord.ui.RoleSelect):
    def __init__(self, purpose: str) -> None:
        super().__init__(
            placeholder="Eine oder mehrere Rollen auswählen",
            min_values=0,
            max_values=25,
        )
        self.purpose = purpose

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        database = interaction.client.db
        if not await require_permission(interaction, database, "settings"):
            return
        await database.replace_roles(
            interaction.guild.id, self.purpose, [role.id for role in self.values]
        )
        await interaction.response.send_message(
            f"✅ **{self.purpose}**: {len(self.values)} Rolle(n) gespeichert.",
            ephemeral=True,
        )


class RoleBindingView(discord.ui.View):
    def __init__(self, purpose: str) -> None:
        super().__init__(timeout=300)
        self.add_item(RoleBindingSelect(purpose))


class ChannelPurposeSelect(discord.ui.Select):
    OPTIONS = {
        "channel.ticket_archive": "Ticketarchiv",
        "channel.application_review": "Bewerbungsprüfung",
        "channel.application_archive": "Bewerbungsarchiv",
        "channel.giveaway_winners": "Giveaway-Gewinner",
        "channel.logs": "Logs",
        "channel.welcome": "Willkommen",
        "channel.leave": "Verabschiedung",
    }

    def __init__(self) -> None:
        super().__init__(
            placeholder="Kanalzweck auswählen",
            options=[
                discord.SelectOption(label=label, value=key) for key, label in self.OPTIONS.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"Kanal für **{self.OPTIONS[self.values[0]]}** auswählen:",
            view=ChannelBindingView(self.values[0]),
            ephemeral=True,
        )


class ChannelBindingSelect(discord.ui.ChannelSelect):
    def __init__(self, purpose: str) -> None:
        super().__init__(
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            placeholder="Textkanal auswählen",
        )
        self.purpose = purpose

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        database = interaction.client.db
        if not await require_permission(interaction, database, "settings"):
            return
        await database.set_setting(interaction.guild.id, self.purpose, self.values[0].id)
        await interaction.response.send_message(
            f"✅ {self.values[0].mention} gespeichert.", ephemeral=True
        )


class ChannelBindingView(discord.ui.View):
    def __init__(self, purpose: str) -> None:
        super().__init__(timeout=300)
        self.add_item(ChannelBindingSelect(purpose))


class SettingsView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=600)

    @discord.ui.button(label="Teamrollen", emoji="👥", style=discord.ButtonStyle.primary)
    async def team(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Teamstufe auswählen:", view=PurposeView("team"), ephemeral=True
        )

    @discord.ui.button(label="Berechtigungen", emoji="🔐", style=discord.ButtonStyle.primary)
    async def permissions(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Berechtigung auswählen:",
            view=PurposeView("permissions"),
            ephemeral=True,
        )

    @discord.ui.button(label="Tickets", emoji="🎫", style=discord.ButtonStyle.secondary)
    async def tickets(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Ticketart auswählen:", view=PurposeView("tickets"), ephemeral=True
        )

    @discord.ui.button(label="Bewerbungen", emoji="📝", style=discord.ButtonStyle.secondary)
    async def applications(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Bewerbungsbereich auswählen:",
            view=PurposeView("applications"),
            ephemeral=True,
        )

    @discord.ui.button(label="Kanäle", emoji="#️⃣", style=discord.ButtonStyle.secondary)
    async def channels(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        view = discord.ui.View(timeout=300)
        view.add_item(ChannelPurposeSelect())
        await interaction.response.send_message("Kanalzweck auswählen:", view=view, ephemeral=True)


class Management(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="settings", description="Öffnet die zentrale Nexoria-Konfiguration.")
    @app_commands.default_permissions(manage_guild=True)
    async def settings(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        await ensure_guild_defaults(self.bot.db, interaction.guild.id)
        if not await require_permission(interaction, self.bot.db, "settings"):
            return
        embed = discord.Embed(
            title="⚙️ Nexoria Craft – Administration",
            description=(
                "Konfiguriere Teamrollen, mehrere Zuständigkeitsrollen, "
                "Berechtigungen und Systemkanäle ohne manuelle IDs.\n\n"
                "Administratoren besitzen immer Notfallzugriff."
            ),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, view=SettingsView(), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Management(bot))
