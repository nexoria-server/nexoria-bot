from __future__ import annotations

import io
import re

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from bot.services import (
    DEFAULT_TICKET_TYPES,
    ensure_guild_defaults,
    require_permission,
    transcript_html,
)


class TicketTypeSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Ticketart auswählen",
            custom_id="nexoria:ticket:type",
            options=[
                discord.SelectOption(
                    label=name,
                    value=key,
                    description=description[:100],
                    emoji=emoji,
                )
                for key, (name, description, emoji) in DEFAULT_TICKET_TYPES.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        database = interaction.client.db
        await ensure_guild_defaults(database, interaction.guild.id)
        ticket_type = await database.fetchone(
            "SELECT * FROM ticket_types WHERE guild_id=? AND type_key=? AND enabled=1",
            (interaction.guild.id, self.values[0]),
        )
        if not ticket_type:
            await interaction.response.send_message(
                "❌ Diese Ticketart ist nicht konfiguriert.", ephemeral=True
            )
            return
        existing = await database.fetchone(
            "SELECT channel_id FROM tickets WHERE guild_id=? AND owner_id=? "
            "AND type_key=? AND status='open'",
            (interaction.guild.id, interaction.user.id, self.values[0]),
        )
        if existing:
            await interaction.response.send_message(
                f"❌ Du hast bereits ein offenes Ticket: <#{existing['channel_id']}>",
                ephemeral=True,
            )
            return
        category = interaction.guild.get_channel(ticket_type["category_id"])
        if not isinstance(category, discord.CategoryChannel):
            fallback = await database.guild_config(interaction.guild.id)
            category = interaction.guild.get_channel(fallback["ticket_category_id"])
        staff_ids = await database.roles(interaction.guild.id, f"ticket.{self.values[0]}.staff")
        if not staff_ids:
            fallback = await database.guild_config(interaction.guild.id)
            if fallback["ticket_staff_role_id"]:
                staff_ids.add(int(fallback["ticket_staff_role_id"]))
        overwrites = {
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
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )
        await interaction.response.defer(ephemeral=True)
        channel = await interaction.guild.create_text_channel(
            name=f"{self.values[0]}-{interaction.user.name}"[:100],
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=overwrites,
            topic=f"Ticket-Ersteller: {interaction.user.id} | Typ: {self.values[0]}",
            reason=f"Ticket von {interaction.user}",
        )
        try:
            ticket_id = (
                await database.execute(
                    "INSERT INTO tickets(guild_id,channel_id,owner_id,type_key) VALUES(?,?,?,?)",
                    (
                        interaction.guild.id,
                        channel.id,
                        interaction.user.id,
                        self.values[0],
                    ),
                )
            ).lastrowid
        except aiosqlite.IntegrityError:
            await channel.delete(reason="Doppeltes Ticket verhindert")
            await interaction.followup.send(
                "Ein Ticket dieser Art wurde gleichzeitig bereits erstellt.", ephemeral=True
            )
            return
        await channel.send(
            interaction.user.mention,
            embed=discord.Embed(
                title=f"{ticket_type['emoji']} Ticket #{ticket_id} – {ticket_type['name']}",
                description=(
                    "Beschreibe dein Anliegen möglichst genau. "
                    "Das zuständige Team wurde freigeschaltet."
                ),
                color=discord.Color.blurple(),
            ),
            view=CloseTicketView(),
        )
        await interaction.followup.send(f"✅ Ticket erstellt: {channel.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())


class CloseReasonModal(discord.ui.Modal, title="Ticket schließen"):
    reason = discord.ui.TextInput(
        label="Abschlussgrund",
        placeholder="Erledigt",
        required=False,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            return
        database = interaction.client.db
        ticket = await database.fetchone(
            "SELECT * FROM tickets WHERE channel_id=? AND status='open'",
            (interaction.channel.id,),
        )
        if not ticket:
            await interaction.response.send_message(
                "❌ Dieses Ticket ist bereits geschlossen.", ephemeral=True
            )
            return
        is_owner = interaction.user.id == ticket["owner_id"]
        staff_ids = await database.roles(interaction.guild.id, f"ticket.{ticket['type_key']}.staff")
        member_roles = {role.id for role in getattr(interaction.user, "roles", [])}
        is_staff = bool(staff_ids & member_roles) or getattr(
            interaction.user.guild_permissions, "administrator", False
        )
        if not is_owner and not is_staff:
            await interaction.response.send_message(
                "❌ Du darfst dieses Ticket nicht schließen.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        messages = [
            message async for message in interaction.channel.history(limit=None, oldest_first=True)
        ]
        transcript = transcript_html(messages, f"Ticket #{ticket['id']}")
        cursor = await database.execute(
            "UPDATE tickets SET status='closed',closed_at=CURRENT_TIMESTAMP,"
            "closed_by=?,close_reason=?,transcript=? "
            "WHERE id=? AND status='open'",
            (
                interaction.user.id,
                str(self.reason) or "Erledigt",
                transcript,
                ticket["id"],
            ),
        )
        if cursor.rowcount != 1:
            await interaction.followup.send(
                "❌ Ticket wurde bereits parallel geschlossen.", ephemeral=True
            )
            return
        ticket_type = await database.fetchone(
            "SELECT archive_channel_id FROM ticket_types WHERE guild_id=? AND type_key=?",
            (interaction.guild.id, ticket["type_key"]),
        )
        archive_id = ticket_type["archive_channel_id"] if ticket_type else 0
        archive_id = archive_id or await database.setting(
            interaction.guild.id, "channel.ticket_archive", 0
        )
        archive = interaction.guild.get_channel(archive_id)
        if isinstance(archive, discord.TextChannel):
            await archive.send(
                embed=discord.Embed(
                    title=f"📚 Ticket #{ticket['id']} archiviert",
                    description=(
                        f"**Ersteller:** <@{ticket['owner_id']}>\n"
                        f"**Typ:** {ticket['type_key']}\n"
                        f"**Geschlossen von:** {interaction.user.mention}\n"
                        f"**Grund:** {str(self.reason) or 'Erledigt'}"
                    ),
                    color=discord.Color.dark_grey(),
                ),
                file=discord.File(
                    io.BytesIO(transcript.encode()),
                    filename=f"ticket-{ticket['id']}.html",
                ),
            )
        await interaction.followup.send(
            "✅ Ticket archiviert. Der Kanal wird gelöscht.", ephemeral=True
        )
        await interaction.channel.delete(reason=f"Ticket #{ticket['id']} geschlossen")


class CloseTicketView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ticket schließen",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="nexoria:ticket:close",
    )
    async def close(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(CloseReasonModal())


class TicketArchiveSearchModal(discord.ui.Modal, title="Ticketarchiv durchsuchen"):
    query = discord.ui.TextInput(
        label="Name, Discord-ID oder Ticket-ID",
        placeholder="123, Benutzername oder Discord-ID",
        required=False,
        max_length=100,
    )
    ticket_type = discord.ui.TextInput(
        label="Ticketart",
        placeholder="support, media, partner ... oder leer",
        required=False,
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        database = interaction.client.db
        if not await require_permission(interaction, database, "ticket_archive"):
            return
        query = str(self.query).strip()
        type_key = str(self.ticket_type).strip().casefold()
        clauses = ["guild_id=?", "status='closed'"]
        parameters: list[object] = [interaction.guild.id]
        if type_key:
            clauses.append("type_key=?")
            parameters.append(type_key)
        if query.isdigit():
            clauses.append("(id=? OR owner_id=?)")
            parameters.extend([int(query), int(query)])
        rows = await database.fetchall(
            "SELECT * FROM tickets WHERE " + " AND ".join(clauses) + " ORDER BY id DESC LIMIT 20",
            tuple(parameters),
        )
        if query and not query.isdigit():
            rows = [
                row
                for row in rows
                if (member := interaction.guild.get_member(row["owner_id"]))
                and query.casefold() in member.display_name.casefold()
            ]
        description = (
            "\n".join(
                f"**#{row['id']}** <@{row['owner_id']}> – {row['type_key']} – "
                f"{row['closed_at']} – {row['close_reason'] or 'ohne Grund'}"
                for row in rows
            )
            or "Keine archivierten Tickets gefunden."
        )
        exact = next((row for row in rows if query.isdigit() and row["id"] == int(query)), None)
        file = None
        if exact and exact["transcript"]:
            file = discord.File(
                io.BytesIO(exact["transcript"].encode("utf-8")),
                filename=f"ticket-{exact['id']}.html",
            )
        await interaction.response.send_message(
            embed=discord.Embed(title="📚 Ticketarchiv", description=description[:4000]),
            file=file,
            ephemeral=True,
        )


class TicketArchiveView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ticket suchen",
        emoji="🔎",
        style=discord.ButtonStyle.primary,
        custom_id="nexoria:ticket:archive:search",
    )
    async def search(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketArchiveSearchModal())


class TicketTypeModal(discord.ui.Modal, title="Ticketart konfigurieren"):
    type_key = discord.ui.TextInput(label="Schlüssel", placeholder="support", max_length=30)
    name = discord.ui.TextInput(label="Anzeigename", placeholder="Support", max_length=80)
    description = discord.ui.TextInput(
        label="Beschreibung", style=discord.TextStyle.paragraph, max_length=300
    )
    emoji = discord.ui.TextInput(label="Emoji", placeholder="🎫", max_length=20)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        if not await require_permission(interaction, interaction.client.db, "settings"):
            return
        key = re.sub(r"[^a-z0-9_-]", "", str(self.type_key).casefold())
        if not key:
            await interaction.response.send_message("❌ Ungültiger Schlüssel.", ephemeral=True)
            return
        await interaction.client.db.execute(
            "INSERT INTO ticket_types(guild_id,type_key,name,description,emoji) "
            "VALUES(?,?,?,?,?) ON CONFLICT(guild_id,type_key) DO UPDATE SET "
            "name=excluded.name,description=excluded.description,emoji=excluded.emoji",
            (
                interaction.guild.id,
                key,
                str(self.name),
                str(self.description),
                str(self.emoji),
            ),
        )
        await interaction.response.send_message(
            f"✅ Ticketart **{key}** gespeichert.", ephemeral=True
        )


class Tickets(commands.GroupCog, group_name="ticket", group_description="Tickets"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.close_view = CloseTicketView()

    async def cog_load(self) -> None:
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(self.close_view)
        self.bot.add_view(TicketArchiveView())

    @app_commands.command(name="open", description="Postet ein Ticketpanel im Zielkanal.")
    @app_commands.default_permissions(manage_guild=True)
    async def open(self, interaction: discord.Interaction, kanal: discord.TextChannel) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "tickets"
        ):
            return
        await ensure_guild_defaults(self.bot.db, interaction.guild.id)
        await kanal.send(
            embed=discord.Embed(
                title="🎫 Nexoria Craft – Tickets",
                description="Wähle den passenden Bereich aus.",
                color=discord.Color.blurple(),
            ),
            view=TicketPanelView(),
        )
        await interaction.response.send_message(
            f"✅ Ticketpanel in {kanal.mention} veröffentlicht.", ephemeral=True
        )

    @app_commands.command(name="panel", description="Kompatibler Alias: postet das Ticketpanel.")
    @app_commands.default_permissions(manage_guild=True)
    async def panel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await self.open.callback(self, interaction, channel)

    @app_commands.command(name="type", description="Erstellt oder bearbeitet eine Ticketart.")
    @app_commands.default_permissions(manage_guild=True)
    async def type(self, interaction: discord.Interaction) -> None:
        if not await require_permission(interaction, self.bot.db, "settings"):
            return
        await interaction.response.send_modal(TicketTypeModal())

    @app_commands.command(name="category", description="Setzt die Kategorie einer Ticketart.")
    @app_commands.default_permissions(manage_guild=True)
    async def category(
        self,
        interaction: discord.Interaction,
        ticketart: str,
        kategorie: discord.CategoryChannel,
    ) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "settings"
        ):
            return
        await ensure_guild_defaults(self.bot.db, interaction.guild.id)
        await self.bot.db.execute(
            "UPDATE ticket_types SET category_id=? WHERE guild_id=? AND type_key=?",
            (kategorie.id, interaction.guild.id, ticketart.casefold()),
        )
        await interaction.response.send_message(
            f"✅ Kategorie für **{ticketart}** gespeichert.", ephemeral=True
        )

    @app_commands.command(name="archive", description="Postet das Ticketarchiv-Panel.")
    @app_commands.default_permissions(manage_guild=True)
    async def archive(self, interaction: discord.Interaction, kanal: discord.TextChannel) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "ticket_archive"
        ):
            return
        await kanal.send(
            embed=discord.Embed(
                title="📚 Ticketarchiv",
                description=(
                    "Suche nach Ticket-ID, Discord-ID, Name und Ticketart. "
                    "Transkripte bleiben dauerhaft in der Datenbank gespeichert."
                ),
                color=discord.Color.blurple(),
            ),
            view=TicketArchiveView(),
        )
        await interaction.response.send_message(
            f"✅ Ticketarchiv in {kanal.mention} veröffentlicht.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
