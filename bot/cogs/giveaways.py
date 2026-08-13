from __future__ import annotations

import random
import time

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks


class GiveawayView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Teilnehmen",
        emoji="🎁",
        style=discord.ButtonStyle.success,
        custom_id="nexoria:giveaway:enter",
    )
    async def enter(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not interaction.message:
            return
        giveaway = await self.bot.db.fetchone(
            "SELECT ended FROM giveaways WHERE message_id=? AND guild_id=?",
            (interaction.message.id, interaction.guild.id),
        )
        if not giveaway or giveaway["ended"]:
            await interaction.response.send_message(
                "Dieses Giveaway ist bereits beendet.", ephemeral=True
            )
            return
        try:
            await self.bot.db.execute(
                "INSERT INTO giveaway_entries(message_id,user_id) VALUES(?,?)",
                (interaction.message.id, interaction.user.id),
            )
        except aiosqlite.IntegrityError:
            await interaction.response.send_message(
                "Du nimmst bereits teil.", ephemeral=True
            )
            return
        await interaction.response.send_message("🎉 Teilnahme gespeichert!", ephemeral=True)


class Giveaways(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(GiveawayView(self.bot))
        self.finish_loop.start()

    def cog_unload(self) -> None:
        self.finish_loop.cancel()

    @app_commands.command(name="giveaway", description="Startet oder beendet ein Giveaway.")
    @app_commands.choices(
        aktion=[
            app_commands.Choice(name="Start", value="start"),
            app_commands.Choice(name="Ende", value="end"),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway(
        self,
        interaction: discord.Interaction,
        aktion: app_commands.Choice[str],
        minuten: app_commands.Range[int, 1, 10080] | None = None,
        gewinner: app_commands.Range[int, 1, 20] | None = None,
        preis: str | None = None,
    ) -> None:
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("❌ Ungültiger Kanal.", ephemeral=True)
            return
        if aktion.value == "start":
            if not minuten or not gewinner or not preis:
                await interaction.response.send_message(
                    "Start benötigt Minuten, Gewinnerzahl und Preis.", ephemeral=True
                )
                return
            end = time.time() + minuten * 60
            embed = discord.Embed(
                title="🎁 Giveaway",
                description=(
                    f"**Preis:** {preis}\n"
                    f"**Gewinner:** {gewinner}\n"
                    f"**Ende:** <t:{int(end)}:R>"
                ),
                color=discord.Color.gold(),
            )
            await interaction.response.send_message(embed=embed, view=GiveawayView(self.bot))
            message = await interaction.original_response()
            await self.bot.db.execute(
                "INSERT INTO giveaways("
                "message_id,guild_id,channel_id,prize,end_at,winners,ended"
                ") VALUES(?,?,?,?,?,?,0)",
                (
                    message.id,
                    interaction.guild.id,
                    interaction.channel.id,
                    preis,
                    end,
                    gewinner,
                ),
            )
            return

        rows = await self.bot.db.fetchall(
            "SELECT message_id FROM giveaways "
            "WHERE guild_id=? AND channel_id=? AND ended=0 ORDER BY end_at DESC",
            (interaction.guild.id, interaction.channel.id),
        )
        if not rows:
            await interaction.response.send_message("Kein aktives Giveaway.", ephemeral=True)
            return
        await self.finish(rows[0]["message_id"])
        await interaction.response.send_message("🎁 Giveaway beendet.", ephemeral=True)

    async def finish(self, message_id: int) -> None:
        giveaway = await self.bot.db.fetchone(
            "SELECT * FROM giveaways WHERE message_id=?", (message_id,)
        )
        if not giveaway or giveaway["ended"]:
            return
        cursor = await self.bot.db.execute(
            "UPDATE giveaways SET ended=1 WHERE message_id=? AND ended=0", (message_id,)
        )
        if cursor.rowcount != 1:
            return
        entries = await self.bot.db.fetchall(
            "SELECT user_id FROM giveaway_entries WHERE message_id=?", (message_id,)
        )
        picks = random.sample(entries, min(giveaway["winners"], len(entries))) if entries else []
        channel = self.bot.get_channel(giveaway["channel_id"])
        if isinstance(channel, discord.TextChannel):
            mentions = ", ".join(f"<@{entry['user_id']}>" for entry in picks)
            await channel.send(
                f"🎉 Giveaway beendet! **{giveaway['prize']}** — "
                f"Gewinner: {mentions or 'keine'}",
                allowed_mentions=discord.AllowedMentions(users=True),
            )

    @tasks.loop(seconds=30)
    async def finish_loop(self) -> None:
        rows = await self.bot.db.fetchall(
            "SELECT message_id FROM giveaways WHERE ended=0 AND end_at<=?",
            (time.time(),),
        )
        for row in rows:
            await self.finish(row["message_id"])

    @finish_loop.before_loop
    async def before_finish_loop(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Giveaways(bot))
