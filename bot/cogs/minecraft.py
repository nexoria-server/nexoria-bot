from __future__ import annotations

import asyncio
import hashlib
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks
from mcstatus import JavaServer

from bot.config import settings
from bot.services import require_permission

log = logging.getLogger(__name__)


class MinecraftView(discord.ui.View):
    def __init__(self, cog: "Minecraft") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Aktualisieren",
        emoji="🔄",
        style=discord.ButtonStyle.primary,
        custom_id="nexoria:minecraft:refresh",
    )
    async def refresh(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild:
            return
        await interaction.response.defer(ephemeral=True)
        await self.cog.update_guild(interaction.guild, force=True)
        await interaction.followup.send("Status aktualisiert.", ephemeral=True)

    @discord.ui.button(
        label="Server-IP",
        emoji="🌐",
        style=discord.ButtonStyle.secondary,
        custom_id="nexoria:minecraft:ip",
    )
    async def server_ip(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            f"☕ **Java:** `{settings.MC_SERVER_HOST}:{settings.MC_SERVER_PORT}`\n"
            f"📱 **Bedrock:** `{settings.MC_BEDROCK_HOST}:{settings.MC_BEDROCK_PORT}`",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Online-Spieler",
        emoji="👥",
        style=discord.ButtonStyle.secondary,
        custom_id="nexoria:minecraft:players",
    )
    async def players(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await require_permission(interaction, interaction.client.db, "minecraft_details"):
            return
        status = await self.cog.get_status()
        names = status["names"]
        await interaction.response.send_message(
            "**Aktuell online:**\n"
            + (
                "\n".join(f"• `{name}`" for name in names)
                if names
                else "Niemand oder keine Spielerliste verfügbar."
            ),
            ephemeral=True,
        )


class Minecraft(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._query_lock = asyncio.Lock()

    async def cog_load(self) -> None:
        self.bot.add_view(MinecraftView(self))
        self.update_panel_loop.change_interval(seconds=settings.MC_UPDATE_SECONDS)
        self.update_panel_loop.start()

    def cog_unload(self) -> None:
        self.update_panel_loop.cancel()

    async def get_status(self) -> dict:
        async with self._query_lock:
            try:
                server = await JavaServer.async_lookup(
                    f"{settings.MC_SERVER_HOST}:{settings.MC_SERVER_PORT}"
                )
                status = await asyncio.wait_for(server.async_status(), timeout=8)
                sample = status.players.sample or []
                return {
                    "online": True,
                    "players": status.players.online,
                    "max_players": status.players.max,
                    "ping": round(status.latency),
                    "names": [getattr(player, "name", str(player)) for player in sample],
                }
            except (TimeoutError, OSError, ValueError):
                return {
                    "online": False,
                    "players": 0,
                    "max_players": 0,
                    "ping": 0,
                    "names": [],
                }
            except Exception:
                log.exception("Minecraft-Statusabfrage fehlgeschlagen")
                return {
                    "online": False,
                    "players": 0,
                    "max_players": 0,
                    "ping": 0,
                    "names": [],
                }

    async def create_panel(self, mode: str) -> discord.Embed:
        status = await self.get_status()
        if mode == "wartung":
            status_text, color = "🟠 Wartung", discord.Color.orange()
        elif status["online"]:
            status_text, color = "🟢 Online", discord.Color.green()
        else:
            status_text, color = "🔴 Offline", discord.Color.red()

        embed = discord.Embed(
            title="🎮 NexoriaCraft",
            description="**Minecraft Server Status**",
            color=color,
        )
        embed.add_field(name="📡 Status", value=status_text)
        embed.add_field(
            name="👥 Spieler",
            value=f"`{status['players']}/{status['max_players']}`",
        )
        embed.add_field(
            name="📶 Ping",
            value=f"`{status['ping']} ms`" if status["online"] else "`Nicht erreichbar`",
        )
        embed.add_field(
            name="☕ Java",
            value=f"`{settings.MC_SERVER_HOST}:{settings.MC_SERVER_PORT}`",
            inline=False,
        )
        embed.add_field(
            name="📱 Bedrock",
            value=f"`{settings.MC_BEDROCK_HOST}:{settings.MC_BEDROCK_PORT}`",
            inline=False,
        )
        embed.set_footer(text="NexoriaCraft • automatischer Serverstatus")
        return embed

    async def update_guild(self, guild: discord.Guild, *, force: bool = False) -> None:
        row = await self.bot.db.fetchone(
            "SELECT * FROM minecraft_panels WHERE guild_id=?", (guild.id,)
        )
        if not row:
            return
        channel = guild.get_channel(row["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return
        embed = await self.create_panel(row["mode"])
        payload_hash = hashlib.sha256(str(embed.to_dict()).encode()).hexdigest()
        if not force and payload_hash == row["payload_hash"]:
            return
        try:
            message = await channel.fetch_message(row["message_id"])
            await message.edit(embed=embed, view=MinecraftView(self))
        except (discord.NotFound, discord.Forbidden):
            log.warning("Minecraft-Panel in Guild %s ist nicht mehr erreichbar", guild.id)
            return
        await self.bot.db.execute(
            "UPDATE minecraft_panels SET payload_hash=? WHERE guild_id=?",
            (payload_hash, guild.id),
        )

    @app_commands.command(name="minecraft", description="Erstellt das Minecraft-Statuspanel.")
    @app_commands.default_permissions(manage_guild=True)
    async def minecraft(
        self, interaction: discord.Interaction, channel: discord.TextChannel | None = None
    ) -> None:
        if not interaction.guild:
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("❌ Ungültiger Kanal.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        old = await self.bot.db.fetchone(
            "SELECT mode FROM minecraft_panels WHERE guild_id=?", (interaction.guild.id,)
        )
        mode = old["mode"] if old else "offen"
        embed = await self.create_panel(mode)
        message = await target.send(embed=embed, view=MinecraftView(self))
        digest = hashlib.sha256(str(embed.to_dict()).encode()).hexdigest()
        await self.bot.db.execute(
            "INSERT INTO minecraft_panels(guild_id,channel_id,message_id,mode,payload_hash) "
            "VALUES(?,?,?,?,?) ON CONFLICT(guild_id) DO UPDATE SET "
            "channel_id=excluded.channel_id,message_id=excluded.message_id,"
            "payload_hash=excluded.payload_hash",
            (interaction.guild.id, target.id, message.id, mode, digest),
        )
        await interaction.followup.send(
            f"✅ Minecraft-Statuspanel in {target.mention} erstellt.", ephemeral=True
        )

    @app_commands.command(name="minecraft_status", description="Setzt den Minecraft-Serverstatus.")
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Wartung", value="wartung"),
            app_commands.Choice(name="Offen", value="offen"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    async def minecraft_status(
        self, interaction: discord.Interaction, status: app_commands.Choice[str]
    ) -> None:
        if not interaction.guild:
            return
        await self.bot.db.execute(
            "UPDATE minecraft_panels SET mode=? WHERE guild_id=?",
            (status.value, interaction.guild.id),
        )
        await interaction.response.send_message(
            f"✅ Minecraft-Status auf **{status.name}** gesetzt.", ephemeral=True
        )
        await self.update_guild(interaction.guild, force=True)

    @tasks.loop(seconds=15)
    async def update_panel_loop(self) -> None:
        for guild in self.bot.guilds:
            await self.update_guild(guild)

    @update_panel_loop.before_loop
    async def before_update_panel_loop(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Minecraft(bot))
