import asyncio
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import settings


# ============================================================
# NEXORIA TICKET KONFIGURATION
# ============================================================

# Deine Ticket-Kategorie
TICKET_CATEGORY_ID = settings.TICKET_CATEGORY_ID

# Deine @Nexoria Staff Team Rolle
STAFF_ROLE_ID = settings.TICKET_STAFF_ROLE_ID


# ============================================================
# TICKET-TYPEN
# ============================================================

TICKET_TYPES = {
    "general": {
        "label": "Allgemeiner Support",
        "emoji": "🎫",
        "description": "Allgemeine Fragen und Anliegen",
    },
    "ingame": {
        "label": "Ingame Support",
        "emoji": "🎮",
        "description": "Hilfe bei Problemen im Spiel",
    },
    "report": {
        "label": "Spieler melden",
        "emoji": "🚨",
        "description": "Melde einen Spieler beim Support",
    },
    "unban": {
        "label": "Entbannungsantrag",
        "emoji": "🔓",
        "description": "Stelle einen Antrag auf Entbannung",
    },
    "other": {
        "label": "Sonstiges",
        "emoji": "❓",
        "description": "Andere Anliegen",
    },
}


# ============================================================
# LOGGING
# ============================================================

async def send_ticket_log(bot, guild, message):
    """Schreibt Ticket-Aktionen in den konfigurierten Log-Kanal."""

    try:
        if not hasattr(bot, "db"):
            return

        config = await bot.db.guild_config(guild.id)

        log_channel_id = config["log_channel_id"]

        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))

        if log_channel is None:
            return

        embed = discord.Embed(
            title="🎫 Ticket-Log",
            description=message,
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )

        await log_channel.send(embed=embed)

    except Exception as error:
        print(f"[Ticket-Log] Fehler: {error}")


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

async def get_staff_role(bot, guild: discord.Guild):
    config = await bot.db.guild_config(guild.id)
    role_id = int(config["ticket_staff_role_id"] or STAFF_ROLE_ID)
    return guild.get_role(role_id)


async def is_staff(bot, member: discord.Member) -> bool:
    role = await get_staff_role(bot, member.guild)

    return role is not None and role in member.roles


def get_ticket_owner_id(channel: discord.TextChannel):
    """
    Liest die User-ID aus dem Topic des Tickets.
    """

    if not channel.topic:
        return None

    prefix = "Ticket-Ersteller: "

    for part in channel.topic.split("|"):
        part = part.strip()

        if part.startswith(prefix):
            value = part[len(prefix):].strip()

            try:
                return int(value)
            except ValueError:
                return None

    return None


# ============================================================
# TICKET SCHLIESSEN
# ============================================================

class CloseTicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ticket schließen",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="nexoria_ticket_close",
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None:
            return

        if not isinstance(
            interaction.channel,
            discord.TextChannel,
        ):
            await interaction.response.send_message(
                "❌ Dieses Ticket kann hier nicht geschlossen werden.",
                ephemeral=True,
            )
            return

        member = interaction.user

        # Prüfen, ob Staff oder Ticket-Ersteller
        staff = isinstance(member, discord.Member) and await is_staff(
            interaction.client, member
        )

        owner_id = get_ticket_owner_id(interaction.channel)

        owner = owner_id == member.id

        if not staff and not owner:
            await interaction.response.send_message(
                "❌ Nur der Ticket-Ersteller oder das "
                "Nexoria Staff Team kann dieses Ticket schließen.",
                ephemeral=True,
            )
            return

        # SOFORT auf die Interaction antworten.
        # Dadurch entsteht kein "hat nicht rechtzeitig reagiert".
        await interaction.response.send_message(
            "🔒 Dieses Ticket wird in **5 Sekunden** geschlossen."
        )

        # Log VOR dem Löschen schreiben
        await send_ticket_log(
            interaction.client,
            interaction.guild,
            (
                f"**Ticket geschlossen:** "
                f"{interaction.channel.mention}\n"
                f"**Geschlossen von:** {member.mention}"
            ),
        )

        # 5 Sekunden warten
        await asyncio.sleep(5)

        try:
            await interaction.channel.delete(
                reason=f"Ticket geschlossen von {member}"
            )

        except discord.Forbidden:
            print(
                "[Tickets] Der Bot darf den Ticket-Kanal "
                "nicht löschen. 'Kanäle verwalten' fehlt."
            )

            try:
                await interaction.followup.send(
                    "❌ Ich konnte das Ticket nicht löschen.\n\n"
                    "Dem Bot fehlt wahrscheinlich die Berechtigung "
                    "**Kanäle verwalten**.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                pass

        except discord.NotFound:
            # Kanal wurde bereits gelöscht.
            pass

        except discord.HTTPException as error:
            print(
                f"[Tickets] Discord-Fehler beim Löschen: {error}"
            )

            try:
                await interaction.followup.send(
                    "❌ Beim Löschen des Tickets ist ein Discord-Fehler "
                    "aufgetreten. Bitte informiere das Staff-Team.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                pass

        except Exception as error:
            print(
                f"[Tickets] Unerwarteter Fehler beim Löschen: {error}"
            )


# ============================================================
# TICKET AUSWAHL
# ============================================================

class TicketSelect(discord.ui.Select):

    def __init__(self):

        options = [
            discord.SelectOption(
                label=data["label"],
                description=data["description"],
                emoji=data["emoji"],
                value=key,
            )
            for key, data in TICKET_TYPES.items()
        ]

        super().__init__(
            placeholder="🎫 Wähle den passenden Bereich aus...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="nexoria_ticket_select",
        )

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ Dieses Ticket-System kann nur auf einem Server "
                "verwendet werden.",
                ephemeral=True,
            )
            return

        ticket_type = self.values[0]
        ticket_data = TICKET_TYPES[ticket_type]

        config = await interaction.client.db.guild_config(guild.id)
        category_id = int(config["ticket_category_id"] or TICKET_CATEGORY_ID)

        # Kategorie suchen
        category = guild.get_channel(category_id)

        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "❌ Die konfigurierte Ticket-Kategorie wurde nicht gefunden.\n\n"
                f"ID: `{category_id or 'nicht konfiguriert'}`",
                ephemeral=True,
            )
            return

        # Staff-Rolle suchen
        staff_role = await get_staff_role(interaction.client, guild)

        if staff_role is None:
            await interaction.response.send_message(
                "❌ Die konfigurierte Staff-Rolle wurde nicht gefunden.\n\n"
                f"ID: `{int(config['ticket_staff_role_id'] or STAFF_ROLE_ID) or 'nicht konfiguriert'}`",
                ephemeral=True,
            )
            return

        # --------------------------------------------------------
        # Prüfen, ob bereits ein Ticket existiert
        # --------------------------------------------------------

        existing_ticket = None

        for channel in guild.text_channels:

            if channel.category_id != category.id:
                continue

            owner_id = get_ticket_owner_id(channel)

            if owner_id == interaction.user.id:
                existing_ticket = channel
                break

        if existing_ticket:
            await interaction.response.send_message(
                (
                    "❌ Du hast bereits ein offenes Ticket:\n"
                    f"{existing_ticket.mention}"
                ),
                ephemeral=True,
            )
            return

        # --------------------------------------------------------
        # Ticket-Name
        # --------------------------------------------------------

        username = interaction.user.name.lower()

        safe_username = "".join(
            character
            if character.isalnum() or character in "-_"
            else "-"
            for character in username
        )

        safe_username = safe_username[:20]

        channel_name = f"ticket-{safe_username}"

        # --------------------------------------------------------
        # Berechtigungen
        # --------------------------------------------------------

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),

            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                attach_files=True,
                embed_links=True,
            ),
        }

        # --------------------------------------------------------
        # Bot-Berechtigungen
        # --------------------------------------------------------

        bot_member = guild.me

        if bot_member is not None:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                manage_channels=True,
                attach_files=True,
                embed_links=True,
            )

        # --------------------------------------------------------
        # Ticket erstellen
        # --------------------------------------------------------

        try:

            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=(
                    f"Ticket-Ersteller: {interaction.user.id} | "
                    f"Ticket-Typ: {ticket_type}"
                ),
                reason=(
                    f"Nexoria Ticket - "
                    f"{ticket_data['label']}"
                ),
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                (
                    "❌ Ich konnte das Ticket nicht erstellen.\n\n"
                    "Bitte gib dem Bot die Berechtigung "
                    "**Kanäle verwalten**."
                ),
                ephemeral=True,
            )
            return

        except discord.HTTPException as error:

            print(
                f"[Tickets] Fehler beim Erstellen: {error}"
            )

            await interaction.response.send_message(
                (
                    "❌ Beim Erstellen des Tickets ist ein "
                    "Discord-Fehler aufgetreten."
                ),
                ephemeral=True,
            )
            return

        # --------------------------------------------------------
        # Ticket Embed
        # --------------------------------------------------------

        embed = discord.Embed(
            title=(
                f"{ticket_data['emoji']} "
                f"{ticket_data['label']}"
            ),
            description=(
                f"Hallo {interaction.user.mention}! 👋\n\n"
                "vielen Dank, dass du den **Nexoria Support** "
                "kontaktierst.\n\n"
                "Bitte beschreibe dein Anliegen möglichst genau "
                "und füge bei Bedarf Screenshots oder weitere "
                "Informationen hinzu.\n\n"
                "Unser **Support-Team wird sich "
                "schnellstmöglich bei dir melden.**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "⚠️ **Wichtiger Hinweis**\n"
                "Bitte erstelle Tickets nur, wenn du tatsächlich "
                "Unterstützung benötigst."
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="📌 Bereich",
            value=ticket_data["label"],
            inline=True,
        )

        embed.add_field(
            name="👤 Erstellt von",
            value=interaction.user.mention,
            inline=True,
        )

        embed.set_footer(
            text="Nexoria Support • Bitte habe etwas Geduld."
        )

        # --------------------------------------------------------
        # Staff-Ping + Ticket-Nachricht
        # --------------------------------------------------------

        try:

            await ticket_channel.send(
                content=(
                    f"{interaction.user.mention} "
                    f"{staff_role.mention}"
                ),
                embed=embed,
                view=CloseTicketView(),
            )

        except discord.HTTPException as error:

            print(
                f"[Tickets] Fehler beim Senden der Ticket-Nachricht: "
                f"{error}"
            )

        # --------------------------------------------------------
        # User bestätigen
        # --------------------------------------------------------

        await interaction.response.send_message(
            (
                "✅ Dein Ticket wurde erfolgreich erstellt:\n"
                f"{ticket_channel.mention}"
            ),
            ephemeral=True,
        )

        # --------------------------------------------------------
        # Log
        # --------------------------------------------------------

        await send_ticket_log(
            interaction.client,
            guild,
            (
                f"**Ticket erstellt:** "
                f"{ticket_channel.mention}\n"
                f"**Ersteller:** {interaction.user.mention}\n"
                f"**Bereich:** {ticket_data['label']}"
            ),
        )


# ============================================================
# TICKET PANEL VIEW
# ============================================================

class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(TicketSelect())


# ============================================================
# TICKETS COG
# ============================================================

class Tickets(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Persistente Views registrieren
        bot.add_view(TicketPanelView())
        bot.add_view(CloseTicketView())

    # --------------------------------------------------------
    # /ticket
    # --------------------------------------------------------

    @app_commands.command(
        name="ticket",
        description="Erstellt das Nexoria Ticket-Panel.",
    )
    @app_commands.default_permissions(
        manage_guild=True
    )
    async def ticket(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):

        embed = discord.Embed(
            title="🎫 Nexoria Support",
            description=(
                "Willkommen beim **Nexoria Support**! 👋\n\n"
                "Bitte erstelle ein Ticket **nur, wenn du "
                "tatsächlich Unterstützung benötigst**.\n\n"
                "Beschreibe dein Anliegen möglichst genau, "
                "damit unser Support-Team dir schnell helfen kann.\n\n"
                "Unser **Support-Team wird sich schnellstmöglich "
                "bei dir melden.**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🎫 **Wähle unten den passenden Bereich aus.**"
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="📋 Verfügbare Bereiche",
            value=(
                "🎫 **Allgemeiner Support**\n"
                "🎮 **Ingame Support**\n"
                "🚨 **Spieler melden**\n"
                "🔓 **Entbannungsantrag**\n"
                "❓ **Sonstiges**"
            ),
            inline=False,
        )

        embed.add_field(
            name="⚠️ Bitte beachten",
            value=(
                "Bitte öffne nur ein Ticket, wenn du ein echtes "
                "Anliegen hast. Missbrauch des Ticketsystems kann "
                "Konsequenzen haben."
            ),
            inline=False,
        )

        embed.set_footer(
            text="Nexoria Support • Wir helfen dir gerne weiter."
        )

        try:

            await channel.send(
                embed=embed,
                view=TicketPanelView(),
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                (
                    "❌ Ich kann in diesem Kanal keine Nachrichten "
                    "senden."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            (
                "✅ Das Nexoria Ticket-Panel wurde in "
                f"{channel.mention} erstellt."
            ),
            ephemeral=True,
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(Tickets(bot))
