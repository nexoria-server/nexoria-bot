
import asyncio

import discord
from discord import app_commands
from discord.ext import commands, tasks
from mcstatus import JavaServer


# ============================================================
# KONFIGURATION
# ============================================================

JAVA_HOST = "NexoriaCraft.de"
JAVA_PORT = 25565

BEDROCK_HOST = "NexoriaCraft.de"
BEDROCK_PORT = 1932

PANEL_UPDATE_MINUTES = 2


# ============================================================
# MINECRAFT COG
# ============================================================

class Minecraft(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Panel
        self.panel_message_id = None
        self.panel_channel_id = None

        # Manueller Serverstatus
        # "offen" = normaler Serverbetrieb
        # "wartung" = Wartung
        self.server_mode = "offen"

        # Automatische Aktualisierung
        self.update_panel_loop.start()

    def cog_unload(self):
        self.update_panel_loop.cancel()

    # ========================================================
    # JAVA SERVER ABFRAGEN
    # ========================================================

    async def get_java_status(self):
        def query():
            server = JavaServer(JAVA_HOST, JAVA_PORT)
            return server.status()

        try:
            return await asyncio.to_thread(query)

        except Exception:
            return None

    # ========================================================
    # STATUS
    # ========================================================

    async def get_status(self):
        status = await self.get_java_status()

        if status is None:
            return {
                "online": False,
                "players": 0,
                "max_players": 0,
                "ping": 0,
            }

        return {
            "online": True,
            "players": status.players.online,
            "max_players": status.players.max,
            "ping": round(status.latency),
        }

    # ========================================================
    # EMBED
    # ========================================================

    async def create_panel(self):
        status = await self.get_status()

        if self.server_mode == "wartung":
            status_text = "🟠 Wartung"
            color = discord.Color.orange()

        elif status["online"]:
            status_text = "🟢 Online"
            color = discord.Color.green()

        else:
            status_text = "🔴 Offline"
            color = discord.Color.red()

        embed = discord.Embed(
            title="🎮 NexoriaCraft",
            description="**Minecraft Server Status**",
            color=color,
        )

        embed.add_field(
            name="📡 Status",
            value=status_text,
            inline=True,
        )

        if status["online"]:
            embed.add_field(
                name="👥 Spieler",
                value=f"`{status['players']}/{status['max_players']}`",
                inline=True,
            )

            embed.add_field(
                name="📶 Ping",
                value=f"`{status['ping']} ms`",
                inline=True,
            )
        else:
            embed.add_field(
                name="👥 Spieler",
                value="`0/0`",
                inline=True,
            )

            embed.add_field(
                name="📶 Ping",
                value="`Nicht erreichbar`",
                inline=True,
            )

        embed.add_field(
            name="☕ Java",
            value=f"`{JAVA_HOST}:{JAVA_PORT}`",
            inline=False,
        )

        embed.add_field(
            name="📱 Bedrock",
            value=f"`{BEDROCK_HOST}:{BEDROCK_PORT}`",
            inline=False,
        )

        if self.server_mode == "wartung":
            embed.add_field(
                name="⚠️ Hinweis",
                value=(
                    "Der Minecraft-Server befindet sich aktuell "
                    "im **Wartungsmodus**."
                ),
                inline=False,
            )

        embed.set_footer(
            text="NexoriaCraft • Automatischer Serverstatus"
        )

        return embed

    # ========================================================
    # BUTTONS
    # ========================================================

    def create_view(self):

        view = discord.ui.View(timeout=None)

        refresh_button = discord.ui.Button(
            label="Aktualisieren",
            emoji="🔄",
            style=discord.ButtonStyle.primary,
            custom_id="minecraft_refresh",
        )

        ip_button = discord.ui.Button(
            label="Server-IP",
            emoji="🌐",
            style=discord.ButtonStyle.secondary,
            custom_id="minecraft_ip",
        )

        async def refresh_callback(interaction):
            embed = await self.create_panel()

            await interaction.response.edit_message(
                embed=embed,
                view=self.create_view(),
            )

        async def ip_callback(interaction):
            await interaction.response.send_message(
                f"☕ **Java:** `{JAVA_HOST}:{JAVA_PORT}`\n"
                f"📱 **Bedrock:** `{BEDROCK_HOST}:{BEDROCK_PORT}`",
                ephemeral=True,
            )

        refresh_button.callback = refresh_callback
        ip_button.callback = ip_callback

        view.add_item(refresh_button)
        view.add_item(ip_button)

        return view

    # ========================================================
    # /minecraft
    # ========================================================

    @app_commands.command(
        name="minecraft",
        description="Zeigt das Minecraft Server Status Panel.",
    )
    async def minecraft(
        self,
        interaction: discord.Interaction,
    ):

        embed = await self.create_panel()

        message = await interaction.channel.send(
            embed=embed,
            view=self.create_view(),
        )

        self.panel_message_id = message.id
        self.panel_channel_id = message.channel.id

        await interaction.response.send_message(
            "✅ Minecraft-Statuspanel wurde erstellt.",
            ephemeral=True,
        )

    # ========================================================
    # /minecraft_status
    # ========================================================

    @app_commands.command(
        name="minecraft_status",
        description="Setzt den Minecraft-Server auf Wartung oder offen.",
    )
    @app_commands.describe(
        status="Gewünschten Serverstatus auswählen.",
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(
                name="Wartung",
                value="wartung",
            ),
            app_commands.Choice(
                name="Offen",
                value="offen",
            ),
        ]
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def minecraft_status(
        self,
        interaction: discord.Interaction,
        status: app_commands.Choice[str],
    ):

        self.server_mode = status.value

        if status.value == "wartung":
            message = (
                "🟠 Der Minecraft-Server wurde auf "
                "**Wartung** gesetzt."
            )
        else:
            message = (
                "🟢 Der Minecraft-Server wurde wieder auf "
                "**Offen** gesetzt."
            )

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

        # Vorhandenes Panel sofort aktualisieren
        await self.update_panel()

    # ========================================================
    # PANEL AKTUALISIEREN
    # ========================================================

    async def update_panel(self):

        if not self.panel_message_id:
            return

        if not self.panel_channel_id:
            return

        try:
            channel = self.bot.get_channel(
                self.panel_channel_id
            )

            if channel is None:
                channel = await self.bot.fetch_channel(
                    self.panel_channel_id
                )

            message = await channel.fetch_message(
                self.panel_message_id
            )

            embed = await self.create_panel()

            await message.edit(
                embed=embed,
                view=self.create_view(),
            )

        except Exception as error:
            print(
                f"[Minecraft] Panel konnte nicht "
                f"aktualisiert werden: {error}"
            )

    # ========================================================
    # AUTOMATISCHE AKTUALISIERUNG
    # ========================================================

    @tasks.loop(minutes=PANEL_UPDATE_MINUTES)
    async def update_panel_loop(self):
        await self.update_panel()

    @update_panel_loop.before_loop
    async def before_update_panel_loop(self):
        await self.bot.wait_until_ready()


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(Minecraft(bot))

