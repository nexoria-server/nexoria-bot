from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.services import require_permission


CATEGORIES = {
    "setup": ("Einrichtung", "⚙️"),
    "tickets": ("Tickets & Archive", "🎫"),
    "applications": ("Bewerbungen", "📝"),
    "team": ("Team & Statistiken", "👥"),
    "moderation": ("Moderation & Sicherheit", "🛡️"),
    "minecraft": ("Minecraft", "⛏️"),
    "giveaways": ("Giveaways", "🎁"),
    "community": ("Community & Inhalte", "📣"),
}


def category_for(name: str) -> str:
    if name in {"settings", "setup", "config", "commands-panel"}:
        return "setup"
    if name.startswith("ticket"):
        return "tickets"
    if name.startswith("application") or "bewerbung" in name:
        return "applications"
    if name.startswith("team"):
        return "team"
    if name in {"warn", "warnings", "clearwarnings", "kick", "ban", "timeout"}:
        return "moderation"
    if name.startswith("security") or name.startswith("verify"):
        return "moderation"
    if name.startswith("minecraft"):
        return "minecraft"
    if name.startswith("giveaway"):
        return "giveaways"
    return "community"


def flatten_commands(tree: app_commands.CommandTree) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []

    def visit(command: app_commands.Command | app_commands.Group, prefix: str = "") -> None:
        qualified = f"{prefix} {command.name}".strip()
        if isinstance(command, app_commands.Group):
            for child in command.commands:
                visit(child, qualified)
            return
        parameters = " ".join(f"<{parameter.name}>" for parameter in command.parameters)
        usage = f"/{qualified} {parameters}".strip()
        result.append((usage, command.description or "Keine Beschreibung"))

    for root in tree.get_commands():
        visit(root)
    return sorted(result, key=lambda item: item[0])


class CommandCategorySelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Command-Bereich auswählen",
            custom_id="nexoria:commands:category",
            options=[
                discord.SelectOption(label=label, value=key, emoji=emoji)
                for key, (label, emoji) in CATEGORIES.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0]
        commands_in_category = [
            (usage, description)
            for usage, description in flatten_commands(interaction.client.tree)
            if category_for(usage.removeprefix("/").split()[0]) == selected
        ]
        lines = [f"**`{usage}`**\n{description}" for usage, description in commands_in_category]
        if selected == "setup":
            lines.append(
                "**Einrichtungsreihenfolge**\n"
                "1. `/settings` – Rollen, Rechte und Kanäle ohne IDs setzen\n"
                "2. `/ticket category` – Kategorien je Ticketart setzen\n"
                "3. Panels mit einem frei gewählten `kanal` veröffentlichen\n"
                "4. Discord-Botrolle über allen automatisch vergebenen Rollen platzieren"
            )
        description = "\n\n".join(lines) or "In diesem Bereich sind keine Commands geladen."
        embed = discord.Embed(
            title=f"{CATEGORIES[selected][1]} {CATEGORIES[selected][0]}",
            description=description[:4096],
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class CommandCenterView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(CommandCategorySelect())


class CommandCenter(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(CommandCenterView())

    @app_commands.command(
        name="commands-panel", description="Postet das permanente, kategorisierte Command-Panel."
    )
    @app_commands.default_permissions(manage_guild=True)
    async def commands_panel(
        self, interaction: discord.Interaction, kanal: discord.TextChannel
    ) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "settings"
        ):
            return
        embed = discord.Embed(
            title="📚 Nexoria Craft – Commands",
            description=(
                "Wähle unten einen Bereich. Die ausführliche Liste wird nur dir angezeigt; "
                "dieses Hauptpanel bleibt dabei unverändert und funktioniert auch nach Neustarts."
            ),
            color=discord.Color.blurple(),
        )
        await kanal.send(embed=embed, view=CommandCenterView())
        await interaction.response.send_message(
            f"✅ Command-Panel in {kanal.mention} erstellt.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommandCenter(bot))
