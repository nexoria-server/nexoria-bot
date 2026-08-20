from __future__ import annotations

import random
import re
import time

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.services import ensure_guild_defaults, require_permission


def _giveaway_id(message: discord.Message | None) -> int | None:
    if not message or not message.embeds or not message.embeds[0].footer.text:
        return None
    match = re.fullmatch(r"giveaway:(\d+)", message.embeds[0].footer.text)
    return int(match.group(1)) if match else None


class GiveawayView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Teilnehmen",
        emoji="🎁",
        style=discord.ButtonStyle.success,
        custom_id="nexoria:giveaway:enter",
    )
    async def enter(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not interaction.message:
            return
        database = interaction.client.db
        giveaway = await database.fetchone(
            "SELECT ended FROM giveaways WHERE message_id=? AND guild_id=?",
            (interaction.message.id, interaction.guild.id),
        )
        if not giveaway or giveaway["ended"]:
            await interaction.response.send_message("Dieses Giveaway ist beendet.", ephemeral=True)
            return
        try:
            await database.execute(
                "INSERT INTO giveaway_entries(message_id,user_id) VALUES(?,?)",
                (interaction.message.id, interaction.user.id),
            )
        except aiosqlite.IntegrityError:
            await interaction.response.send_message("Du nimmst bereits teil.", ephemeral=True)
            return
        await interaction.response.send_message("🎉 Teilnahme gespeichert!", ephemeral=True)


class GiveawayClaimView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Gewinn-Ticket erstellen",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="nexoria:giveaway:claim",
    )
    async def claim(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        message_id = _giveaway_id(interaction.message)
        if message_id is None:
            await interaction.response.send_message("Giveaway-ID fehlt.", ephemeral=True)
            return
        database = interaction.client.db
        winner = await database.fetchone(
            "SELECT * FROM giveaway_winners WHERE message_id=? AND guild_id=? AND user_id=?",
            (message_id, interaction.guild.id, interaction.user.id),
        )
        if not winner:
            await interaction.response.send_message(
                "Nur ausgeloste Gewinner können dieses Ticket erstellen.", ephemeral=True
            )
            return
        if winner["claimed_at"]:
            ticket = await database.fetchone(
                "SELECT channel_id FROM tickets WHERE id=?", (winner["ticket_id"],)
            )
            suffix = f": <#{ticket['channel_id']}>" if ticket else "."
            await interaction.response.send_message(
                f"Dein Gewinn-Ticket wurde bereits erstellt{suffix}", ephemeral=True
            )
            return
        await ensure_guild_defaults(database, interaction.guild.id)
        ticket_type = await database.fetchone(
            "SELECT * FROM ticket_types WHERE guild_id=? AND type_key='giveaway'",
            (interaction.guild.id,),
        )
        category = (
            interaction.guild.get_channel(int(ticket_type["category_id"] or 0))
            if ticket_type
            else None
        )
        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "Die Giveaway-Ticketkategorie ist noch nicht eingerichtet. Nutze /ticket category.",
                ephemeral=True,
            )
            return
        cursor = await database.execute(
            "UPDATE giveaway_winners SET claimed_at=CURRENT_TIMESTAMP "
            "WHERE message_id=? AND guild_id=? AND user_id=? AND claimed_at IS NULL",
            (message_id, interaction.guild.id, interaction.user.id),
        )
        if cursor.rowcount != 1:
            await interaction.response.send_message(
                "Der Gewinn wird bereits eingelöst.", ephemeral=True
            )
            return
        staff_ids = await database.roles(interaction.guild.id, "ticket.giveaway.staff")
        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            ),
        }
        for role_id in staff_ids:
            if role := interaction.guild.get_role(role_id):
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
        try:
            channel = await interaction.guild.create_text_channel(
                name=f"gewinn-{interaction.user.display_name}"[:100],
                category=category,
                overwrites=overwrites,
                reason=f"Giveaway-Gewinn {message_id}",
            )
            ticket_cursor = await database.execute(
                "INSERT INTO tickets(guild_id,channel_id,owner_id,type_key) VALUES(?,?,?,'giveaway')",
                (interaction.guild.id, channel.id, interaction.user.id),
            )
            ticket_id = int(ticket_cursor.lastrowid)
            await database.execute(
                "UPDATE giveaway_winners SET ticket_id=? WHERE message_id=? AND user_id=?",
                (ticket_id, message_id, interaction.user.id),
            )
        except (discord.Forbidden, discord.HTTPException):
            await database.execute(
                "UPDATE giveaway_winners SET claimed_at=NULL WHERE message_id=? AND user_id=? AND ticket_id IS NULL",
                (message_id, interaction.user.id),
            )
            await interaction.response.send_message(
                "Das Ticket konnte nicht erstellt werden. Bitte informiere einen Admin.",
                ephemeral=True,
            )
            return
        from bot.cogs.tickets import CloseTicketView

        embed = discord.Embed(
            title="🎁 Giveaway-Gewinn",
            description=(
                f"Gewinner: {interaction.user.mention}\n"
                f"Gewinn: **{winner['prize']}**\n"
                f"Giveaway-ID: `{message_id}`"
            ),
            color=discord.Color.gold(),
        )
        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=CloseTicketView(),
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        await interaction.response.send_message(
            f"✅ Dein Ticket: {channel.mention}", ephemeral=True
        )


class Giveaways(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(GiveawayView())
        self.bot.add_view(GiveawayClaimView())
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
            await interaction.response.send_message("Ungültiger Kanal.", ephemeral=True)
            return
        if not await require_permission(interaction, self.bot.db, "giveaways"):
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
                    f"**Preis:** {preis}\n**Gewinner:** {gewinner}\n**Ende:** <t:{int(end)}:R>"
                ),
                color=discord.Color.gold(),
            )
            await interaction.response.send_message(embed=embed, view=GiveawayView())
            message = await interaction.original_response()
            await self.bot.db.execute(
                "INSERT INTO giveaways(message_id,guild_id,channel_id,prize,end_at,winners,ended) "
                "VALUES(?,?,?,?,?,?,0)",
                (message.id, interaction.guild.id, interaction.channel.id, preis, end, gewinner),
            )
            return
        row = await self.bot.db.fetchone(
            "SELECT message_id FROM giveaways WHERE guild_id=? AND channel_id=? AND ended=0 "
            "ORDER BY end_at DESC LIMIT 1",
            (interaction.guild.id, interaction.channel.id),
        )
        if not row:
            await interaction.response.send_message("Kein aktives Giveaway.", ephemeral=True)
            return
        await self.finish(row["message_id"])
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
        for entry in picks:
            await self.bot.db.execute(
                "INSERT OR IGNORE INTO giveaway_winners(message_id,guild_id,user_id,prize) "
                "VALUES(?,?,?,?)",
                (message_id, giveaway["guild_id"], entry["user_id"], giveaway["prize"]),
            )
        channel = self.bot.get_channel(giveaway["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return
        mentions = ", ".join(f"<@{entry['user_id']}>" for entry in picks) or "Keine Gewinner"
        embed = discord.Embed(
            title="🎉 Giveaway beendet",
            description=(
                f"**Gewinn:** {giveaway['prize']}\n**Gewinner:** {mentions}\n\n"
                "Nur ausgeloste Gewinner können den Button genau einmal verwenden."
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"giveaway:{message_id}")
        await channel.send(
            embed=embed,
            view=GiveawayClaimView() if picks else None,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        try:
            source = await channel.fetch_message(message_id)
            await source.edit(view=None)
        except (discord.NotFound, discord.Forbidden):
            pass

    @tasks.loop(seconds=30)
    async def finish_loop(self) -> None:
        rows = await self.bot.db.fetchall(
            "SELECT message_id FROM giveaways WHERE ended=0 AND end_at<=?", (time.time(),)
        )
        for row in rows:
            await self.finish(row["message_id"])

    @finish_loop.before_loop
    async def before_finish_loop(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Giveaways(bot))
