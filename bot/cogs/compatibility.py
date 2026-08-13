from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.applications import ApplicationArchiveView, ApplicationPanelView
from bot.config import settings
from bot.services import ensure_guild_defaults, require_permission


class Compatibility(commands.Cog):
    """Behält die ursprünglichen Slash-Command-Namen dauerhaft bei."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="bewerbung_panel", description="Postet wie bisher das Bewerbungs-Panel."
    )
    @app_commands.default_permissions(administrator=True)
    async def bewerbung_panel(
        self,
        interaction: discord.Interaction,
        kanal: discord.TextChannel | None = None,
    ) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "applications"
        ):
            return
        await ensure_guild_defaults(self.bot.db, interaction.guild.id)
        target = kanal or interaction.guild.get_channel(settings.APPLICATION_PANEL_CHANNEL_ID)
        if not isinstance(target, discord.TextChannel):
            target = interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(
                "Kein geeigneter Textkanal gefunden. Gib den Parameter `kanal` an.",
                ephemeral=True,
            )
            return
        embed = discord.Embed(
            title="📝 Nexoria Craft – Bewerbungen",
            description=(
                "Wähle Test Supporter, Builder, Media, Partner, Developer oder "
                "Test Developer aus und fülle das passende Formular aus."
            ),
            color=discord.Color.blurple(),
        )
        await target.send(embed=embed, view=ApplicationPanelView())
        await interaction.response.send_message(
            f"✅ Bewerbungs-Panel in {target.mention} erstellt.", ephemeral=True
        )

    @app_commands.command(
        name="bewerbung_suche", description="Postet wie bisher die Bewerbersuche."
    )
    @app_commands.default_permissions(administrator=True)
    async def bewerbung_suche(
        self,
        interaction: discord.Interaction,
        kanal: discord.TextChannel | None = None,
    ) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "application_archive"
        ):
            return
        target = kanal or interaction.guild.get_channel(settings.APPLICATION_SEARCH_CHANNEL_ID)
        if not isinstance(target, discord.TextChannel):
            target = interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(
                "Kein geeigneter Textkanal gefunden. Gib den Parameter `kanal` an.",
                ephemeral=True,
            )
            return
        embed = discord.Embed(
            title="🗃️ Bewerberverwaltung",
            description="Wähle einen Spieler und danach die gewünschte Bewerbungsart.",
            color=discord.Color.blurple(),
        )
        await target.send(embed=embed, view=ApplicationArchiveView())
        await interaction.response.send_message(
            f"✅ Bewerbersuche in {target.mention} erstellt.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Compatibility(bot))
