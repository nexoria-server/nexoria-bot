from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

# ============================================================
# KONFIGURATION
# ============================================================

ANNOUNCEMENT_PANEL_CHANNEL_ID = 1535968109230301254

DATA_DIR = Path("data")
SCHEDULE_FILE = DATA_DIR / "announcement_schedules.json"
GIVEAWAY_FILE = DATA_DIR / "giveaways.json"

PANEL_TITLE = "📢 Announcement Control Center"

REQUIRE_ADMINISTRATOR = True
ALLOWED_ROLE_IDS: set[int] = set()

LOCK_PANEL_CHANNEL = True

# Kanal, in dem private Claim-Tickets für Giveaway-Gewinner erstellt werden.
GIVEAWAY_CLAIM_CHANNEL_ID = 1536097487364948030

# ============================================================
# KATEGORIEN
# ============================================================

CATEGORY_INFO = {
    "ANNOUNCE": {
        "name": "📢 Announcements",
        "emoji": "📢",
        "color": discord.Color.blurple(),
    },
    "LEAK": {
        "name": "🚨 Leaks",
        "emoji": "🚨",
        "color": discord.Color.red(),
    },
    "EVENT": {
        "name": "🎉 Events",
        "emoji": "🎉",
        "color": discord.Color.gold(),
    },
    "UPDATE": {
        "name": "🔄 Updates",
        "emoji": "🔄",
        "color": discord.Color.blue(),
    },
    "MAINTENANCE": {
        "name": "🛠️ Wartungen",
        "emoji": "🛠️",
        "color": discord.Color.orange(),
    },
    "GIVEAWAY": {
        "name": "🎁 Giveaways",
        "emoji": "🎁",
        "color": discord.Color.green(),
    },
    "PARTNER": {
        "name": "🤝 Partner",
        "emoji": "🤝",
        "color": discord.Color.teal(),
    },
}

DIVIDER = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"

# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = {
    "announcement_1": {
        "name": "📢 Announcement – Clean",
        "category": "ANNOUNCE",
        "title": "Wichtige Ankündigung",
        "text": "Hier kommt deine Ankündigung hinein.",
        "color": discord.Color.blurple(),
        "ping": "",
    },
    "announcement_2": {
        "name": "✨ Announcement – News",
        "category": "ANNOUNCE",
        "title": "✨ Neue News",
        "text": (
            "Wir haben Neuigkeiten für euch!\n\n"
            "Weitere Informationen folgen hier."
        ),
        "color": discord.Color.blue(),
        "ping": "",
    },
    "announcement_3": {
        "name": "📣 Announcement – Community",
        "category": "ANNOUNCE",
        "title": "📣 Community News",
        "text": (
            "Liebe Community,\n\n"
            "hier gibt es ein wichtiges Update für euch."
        ),
        "color": discord.Color.green(),
        "ping": "",
    },
    "announcement_4": {
        "name": "🚀 Announcement – Update",
        "category": "ANNOUNCE",
        "title": "🚀 Server Update",
        "text": (
            "Unser Server hat ein neues Update erhalten.\n\n"
            "**Was ist neu?**\n"
            "• Punkt 1\n"
            "• Punkt 2\n"
            "• Punkt 3"
        ),
        "color": discord.Color.orange(),
        "ping": "",
    },
    "announcement_5": {
        "name": "⭐ Announcement – Important",
        "category": "ANNOUNCE",
        "title": "⭐ Wichtige Information",
        "text": (
            "Diese Information ist für unsere gesamte Community wichtig.\n\n"
            "Bitte lest euch die folgenden Informationen aufmerksam durch."
        ),
        "color": discord.Color.purple(),
        "ping": "",
    },
    "announcement_6": {
        "name": "📜 Announcement – Rules",
        "category": "ANNOUNCE",
        "title": "📜 Neue Regeln",
        "text": (
            "Wir haben unsere Serverregeln aktualisiert.\n\n"
            "Bitte schaut euch die neuen Regeln an und haltet euch daran."
        ),
        "color": discord.Color.dark_blue(),
        "ping": "",
    },
    "announcement_7": {
        "name": "💎 Announcement – Special",
        "category": "ANNOUNCE",
        "title": "💎 Special Announcement",
        "text": (
            "Wir haben etwas Besonderes für euch vorbereitet!\n\n"
            "Weitere Informationen folgen."
        ),
        "color": discord.Color.from_rgb(155, 89, 182),
        "ping": "",
    },
    "announcement_8": {
        "name": "🌟 Announcement – Premium",
        "category": "ANNOUNCE",
        "title": "🌟 Premium Announcement",
        "text": (
            f"{DIVIDER}\n"
            "Wir haben etwas Großes für euch vorbereitet!\n"
            f"{DIVIDER}\n\n"
            "Hier kommt der Haupttext hinein.\n\n"
            "*Bleibt gespannt für mehr Infos.* ✨"
        ),
        "color": discord.Color.from_rgb(241, 196, 15),
        "ping": "",
    },

    "leak_1": {
        "name": "🚨 Leak – Clean",
        "category": "LEAK",
        "title": "🚨 Neuer Leak",
        "text": "Hier kommt die Leak-Information hinein.",
        "color": discord.Color.red(),
        "ping": "",
    },
    "leak_2": {
        "name": "🔴 Leak – Update",
        "category": "LEAK",
        "title": "🔴 Leak Update",
        "text": (
            "Es gibt neue Informationen zu diesem Thema.\n\n"
            "⚠️ Weitere Details folgen."
        ),
        "color": discord.Color.dark_red(),
        "ping": "",
    },
    "leak_3": {
        "name": "👀 Leak – Teaser",
        "category": "LEAK",
        "title": "👀 Kleiner Leak",
        "text": (
            "Wir haben etwas entdeckt, das wir euch "
            "nicht vorenthalten wollen..."
        ),
        "color": discord.Color.purple(),
        "ping": "",
    },
    "leak_4": {
        "name": "🔥 Leak – Major",
        "category": "LEAK",
        "title": "🔥 MAJOR LEAK",
        "text": "Hier kommen die wichtigen Informationen zum Leak hinein.",
        "color": discord.Color.red(),
        "ping": "",
    },
    "leak_5": {
        "name": "💎 Leak – Showcase",
        "category": "LEAK",
        "title": "💎 Leak Showcase",
        "text": (
            "Ein neuer Leak wurde entdeckt.\n\n"
            "📸 Bild/Informationen folgen."
        ),
        "color": discord.Color.from_rgb(155, 89, 182),
        "ping": "",
    },
    "leak_6": {
        "name": "🎬 Leak – Trailer/Preview",
        "category": "LEAK",
        "title": "🎬 Neuer Preview",
        "text": (
            "Ein exklusiver Einblick für unsere Community! 👀\n\n"
            "📌 **Was ihr erwartet:**\n\n"
            "*Mehr Infos folgen in Kürze.*"
        ),
        "color": discord.Color.from_rgb(231, 76, 60),
        "ping": "",
    },

    "event_1": {
        "name": "🎉 Event – Standard",
        "category": "EVENT",
        "title": "🎉 Neues Event",
        "text": (
            "Ein neues Event steht bevor!\n\n"
            "📅 **Datum:**\n"
            "⏰ **Uhrzeit:**\n"
            "📍 **Ort:**\n\n"
            "Wir freuen uns auf euch!"
        ),
        "color": discord.Color.gold(),
        "ping": "",
    },
    "event_2": {
        "name": "🏆 Event – Turnier",
        "category": "EVENT",
        "title": "🏆 Turnier",
        "text": (
            "🏆 **Ein neues Turnier startet!**\n\n"
            "📅 Datum: Noch eintragen\n"
            "⏰ Uhrzeit: Noch eintragen\n"
            "🎮 Spiel: Noch eintragen\n\n"
            "Meldet euch rechtzeitig an!"
        ),
        "color": discord.Color.orange(),
        "ping": "",
    },
    "event_3": {
        "name": "🎁 Event – Giveaway",
        "category": "EVENT",
        "title": "🎁 Giveaway Event",
        "text": (
            "Wir starten ein neues Giveaway!\n\n"
            "🎁 **Gewinn:**\n"
            "⏰ **Ende:**\n"
            "📋 **Teilnahme:**"
        ),
        "color": discord.Color.green(),
        "ping": "",
    },
    "event_4": {
        "name": "🎊 Event – Community",
        "category": "EVENT",
        "title": "🎊 Community Event",
        "text": (
            "Wir veranstalten ein Community Event!\n\n"
            "Kommt vorbei und macht gemeinsam mit."
        ),
        "color": discord.Color.blurple(),
        "ping": "",
    },
    "event_5": {
        "name": "🎆 Event – Saisonal",
        "category": "EVENT",
        "title": "🎆 Saisonales Event",
        "text": (
            f"{DIVIDER}\n"
            "Ein besonderes Event steht vor der Tür! 🎆\n"
            f"{DIVIDER}\n\n"
            "📅 **Datum:**\n"
            "⏰ **Uhrzeit:**\n"
            "🎁 **Belohnungen:**\n\n"
            "*Wir freuen uns riesig auf euch!*"
        ),
        "color": discord.Color.from_rgb(230, 126, 34),
        "ping": "",
    },

    "update_1": {
        "name": "🔄 Update – Standard",
        "category": "UPDATE",
        "title": "🔄 Server Update",
        "text": (
            "Unser Server wurde aktualisiert.\n\n"
            "**Neu:**\n"
            "• Änderung 1\n"
            "• Änderung 2\n"
            "• Änderung 3"
        ),
        "color": discord.Color.blue(),
        "ping": "",
    },
    "update_2": {
        "name": "🚀 Update – Major",
        "category": "UPDATE",
        "title": "🚀 Großes Update",
        "text": (
            "Ein großes Update ist live!\n\n"
            "Wir haben zahlreiche Verbesserungen "
            "und neue Funktionen hinzugefügt."
        ),
        "color": discord.Color.blurple(),
        "ping": "",
    },
    "update_3": {
        "name": "🐛 Update – Bugfix",
        "category": "UPDATE",
        "title": "🐛 Bugfix Update",
        "text": (
            "Wir haben mehrere Fehler behoben.\n\n"
            "Vielen Dank für eure Meldungen!"
        ),
        "color": discord.Color.green(),
        "ping": "",
    },
    "update_4": {
        "name": "✨ Update – Features",
        "category": "UPDATE",
        "title": "✨ Neue Features",
        "text": (
            "Neue Funktionen sind verfügbar!\n\n"
            "• Feature 1\n"
            "• Feature 2\n"
            "• Feature 3"
        ),
        "color": discord.Color.purple(),
        "ping": "",
    },
    "update_5": {
        "name": "📦 Update – Patch Notes",
        "category": "UPDATE",
        "title": "📦 Patch Notes",
        "text": (
            "**🆕 Neu**\n• \n\n"
            "**🛠️ Verbessert**\n• \n\n"
            "**🐛 Behoben**\n• \n\n"
            "*Danke für euer Feedback!*"
        ),
        "color": discord.Color.from_rgb(52, 152, 219),
        "ping": "",
    },

    "maintenance_1": {
        "name": "🛠️ Wartung – Standard",
        "category": "MAINTENANCE",
        "title": "🛠️ Wartungsarbeiten",
        "text": (
            "Auf unserem Server finden Wartungsarbeiten statt.\n\n"
            "📅 **Datum:**\n"
            "⏰ **Beginn:**\n"
            "⏰ **Ende:**\n\n"
            "Vielen Dank für euer Verständnis."
        ),
        "color": discord.Color.orange(),
        "ping": "",
    },
    "maintenance_2": {
        "name": "⚠️ Wartung – Wichtig",
        "category": "MAINTENANCE",
        "title": "⚠️ Wichtige Wartung",
        "text": (
            "Der Server wird für Wartungsarbeiten "
            "kurzzeitig nicht erreichbar sein.\n\n"
            "Bitte beachtet die angegebene Wartungszeit."
        ),
        "color": discord.Color.red(),
        "ping": "",
    },
    "maintenance_3": {
        "name": "🔧 Wartung – Technik",
        "category": "MAINTENANCE",
        "title": "🔧 Technische Wartung",
        "text": (
            "Unser Team führt technische Wartungsarbeiten durch.\n\n"
            "Wir arbeiten daran, den Server schnellstmöglich "
            "wieder vollständig verfügbar zu machen."
        ),
        "color": discord.Color.dark_orange(),
        "ping": "",
    },
    "maintenance_4": {
        "name": "🌙 Wartung – Nacht",
        "category": "MAINTENANCE",
        "title": "🌙 Nächtliche Wartung",
        "text": (
            "Um Störungen für möglichst wenige Mitglieder zu verursachen, "
            "findet die Wartung nachts statt. 🌙\n\n"
            "📅 **Datum:**\n"
            "⏰ **Beginn:**\n"
            "⏰ **Ende:**\n\n"
            "*Danke für euer Verständnis!*"
        ),
        "color": discord.Color.dark_blue(),
        "ping": "",
    },

    "giveaway_1": {
        "name": "🎁 Giveaway – Standard",
        "category": "GIVEAWAY",
        "title": "🎁 Giveaway",
        "text": (
            "Nimm an unserem Giveaway teil!\n\n"
            "🏆 **Gewinn:** Noch eintragen\n"
            "👑 **Gewinner:** 1\n"
            "⏰ **Dauer:** Noch eintragen\n\n"
            "Klicke auf den Teilnahme-Button, um mitzumachen!"
        ),
        "color": discord.Color.green(),
        "ping": "",
    },
    "giveaway_2": {
        "name": "💎 Giveaway – Premium",
        "category": "GIVEAWAY",
        "title": "💎 Premium Giveaway",
        "text": (
            "Ein besonderes Giveaway für unsere Community!\n\n"
            "🎁 **Preis:**\n"
            "🏆 **Gewinner:**\n"
            "⏰ **Ende:**\n\n"
            "Viel Glück!"
        ),
        "color": discord.Color.from_rgb(155, 89, 182),
        "ping": "",
    },
    "giveaway_3": {
        "name": "🏆 Giveaway – Multiple Winners",
        "category": "GIVEAWAY",
        "title": "🏆 Mehrfach-Giveaway",
        "text": (
            "Mehrere Mitglieder können gewinnen!\n\n"
            "🎁 **Preis:**\n"
            "🏆 **Gewinner:** 3\n\n"
            "Jetzt teilnehmen und Glück haben!"
        ),
        "color": discord.Color.gold(),
        "ping": "",
    },
    "giveaway_4": {
        "name": "⚡ Giveaway – Flash",
        "category": "GIVEAWAY",
        "title": "⚡ FLASH GIVEAWAY",
        "text": (
            "Dieses Giveaway läuft nur kurze Zeit!\n\n"
            "🎁 **Gewinn:**\n"
            "⏰ **Dauer:**\n\n"
            "Schnell teilnehmen!"
        ),
        "color": discord.Color.red(),
        "ping": "",
    },
    "giveaway_5": {
        "name": "🌈 Giveaway – Community Milestone",
        "category": "GIVEAWAY",
        "title": "🌈 Milestone-Giveaway",
        "text": (
            f"{DIVIDER}\n"
            "Wir haben ein besonderes Ziel erreicht – als Dankeschön "
            "gibt es ein Giveaway für die ganze Community! 🎉\n"
            f"{DIVIDER}\n\n"
            "🎁 **Preis:**\n"
            "🏆 **Gewinner:**\n"
            "⏰ **Ende:**\n\n"
            "*Danke, dass ihr Teil dieser Community seid!* 💚"
        ),
        "color": discord.Color.from_rgb(46, 204, 113),
        "ping": "",
    },

    "partner_1": {
        "name": "🤝 Partner – Neue Partnerschaft",
        "category": "PARTNER",
        "title": "🤝 Neue Partnerschaft",
        "text": (
            f"{DIVIDER}\n"
            "Wir freuen uns, eine neue Partnerschaft bekannt zu geben!\n"
            f"{DIVIDER}\n\n"
            "🏷️ **Partner:**\n"
            "📝 **Beschreibung:**\n"
            "🔗 **Link:**\n\n"
            "*Schaut gerne mal vorbei!* 👀"
        ),
        "color": discord.Color.teal(),
        "ping": "",
    },
    "partner_2": {
        "name": "💎 Partner – Spotlight",
        "category": "PARTNER",
        "title": "💎 Partner-Spotlight",
        "text": (
            "Heute stellen wir euch einen unserer Partner genauer vor! ✨\n\n"
            "🏷️ **Name:**\n"
            "📝 **Worum geht's:**\n"
            "⭐ **Warum wir sie mögen:**\n"
            "🔗 **Link:**"
        ),
        "color": discord.Color.from_rgb(26, 188, 156),
        "ping": "",
    },
    "partner_3": {
        "name": "📋 Partner – Bewerbung Info",
        "category": "PARTNER",
        "title": "📋 Partner werden",
        "text": (
            f"{DIVIDER}\n"
            "Ihr wollt mit uns eine Partnerschaft eingehen? So geht's:\n"
            f"{DIVIDER}\n\n"
            "**Voraussetzungen:**\n"
            "• Punkt 1\n"
            "• Punkt 2\n"
            "• Punkt 3\n\n"
            "**Bewerbung einreichen:**\n"
            "Schickt uns eine kurze Vorstellung eures Servers/Projekts "
            "inklusive Invite-Link an das Partner-Team.\n\n"
            "*Wir melden uns danach so schnell wie möglich bei euch!* 📬"
        ),
        "color": discord.Color.dark_teal(),
        "ping": "",
    },
    "partner_4": {
        "name": "✅ Partner – Bewerbung angenommen",
        "category": "PARTNER",
        "title": "✅ Bewerbung angenommen",
        "text": (
            "Herzlichen Glückwunsch! 🎉\n\n"
            "Eure Partner-Bewerbung wurde angenommen. Wir freuen uns auf "
            "die Zusammenarbeit!\n\n"
            "📌 **Nächste Schritte:**\n"
        ),
        "color": discord.Color.green(),
        "ping": "",
    },
    "partner_5": {
        "name": "🔻 Partner – Partnerschaft beendet",
        "category": "PARTNER",
        "title": "🔻 Partnerschaft beendet",
        "text": (
            "Wir möchten euch informieren, dass die Partnerschaft mit "
            "folgendem Partner beendet wurde:\n\n"
            "🏷️ **Partner:**\n"
            "📝 **Grund (optional):**\n\n"
            "Wir bedanken uns für die gemeinsame Zeit!"
        ),
        "color": discord.Color.dark_grey(),
        "ping": "",
    },
}

# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def ensure_data_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def utc_now() -> datetime:
    return discord.utils.utcnow()


def datetime_to_string(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def string_to_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def truncate(value: str, length: int = 1024) -> str:
    if not value:
        return value

    if len(value) <= length:
        return value

    return value[: length - 3] + "..."


def valid_url(value: str) -> bool:
    if not value:
        return False

    return bool(
        re.match(
            r"^https?://",
            value.strip(),
            flags=re.IGNORECASE,
        )
    )


def parse_color(
    value: str,
    default: discord.Color,
) -> discord.Color:
    colors = {
        "blue": discord.Color.blue(),
        "blurple": discord.Color.blurple(),
        "red": discord.Color.red(),
        "green": discord.Color.green(),
        "purple": discord.Color.purple(),
        "orange": discord.Color.orange(),
        "gold": discord.Color.gold(),
        "yellow": discord.Color.gold(),
        "dark_red": discord.Color.dark_red(),
        "dark_blue": discord.Color.dark_blue(),
        "dark_green": discord.Color.dark_green(),
        "dark_purple": discord.Color.dark_purple(),
        "dark_orange": discord.Color.dark_orange(),
    }

    value = value.strip().lower()

    if not value:
        return default

    if value in colors:
        return colors[value]

    if re.fullmatch(r"#?[0-9a-fA-F]{6}", value):
        try:
            return discord.Color(
                int(value.replace("#", ""), 16)
            )
        except ValueError:
            pass

    return default


def make_button_view(
    buttons: list[dict],
) -> Optional[discord.ui.View]:
    view = discord.ui.View(timeout=None)

    for button_data in buttons:
        label = button_data.get("label", "").strip()
        url = button_data.get("url", "").strip()
        emoji = button_data.get("emoji", "").strip()

        if not label or not valid_url(url):
            continue

        try:
            view.add_item(
                discord.ui.Button(
                    label=label[:80],
                    url=url,
                    style=discord.ButtonStyle.link,
                    emoji=emoji or None,
                )
            )
        except (ValueError, TypeError):
            view.add_item(
                discord.ui.Button(
                    label=label[:80],
                    url=url,
                    style=discord.ButtonStyle.link,
                )
            )

    if not view.children:
        return None

    return view


def build_embed(
    title: str,
    text: str,
    color: discord.Color,
    author: discord.abc.User | discord.ClientUser | None = None,
    image_url: str | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=text,
        color=color,
        timestamp=utc_now(),
    )

    if author:
        embed.set_footer(
            text=f"Von {author}",
            icon_url=(
                getattr(author.display_avatar, "url", None)
                if hasattr(author, "display_avatar")
                else None
            ),
        )

    if image_url:
        embed.set_image(url=image_url)

    return embed


def make_progress_bar(
    start: datetime,
    end: datetime,
    length: int = 14,
) -> str:
    """
    Baut eine kleine Textbalken-Fortschrittsanzeige, wie viel Zeit
    eines Giveaways bereits verstrichen ist.
    """
    total_seconds = (end - start).total_seconds()

    if total_seconds <= 0:
        fraction = 1.0
    else:
        fraction = (
            utc_now() - start
        ).total_seconds() / total_seconds

    fraction = max(0.0, min(1.0, fraction))

    filled = round(fraction * length)
    bar = "▰" * filled + "▱" * (length - filled)
    percent = int(fraction * 100)

    return f"{bar} `{percent}%`"


async def resolve_channel(
    bot: commands.Bot,
    raw_channel,
) -> Optional[discord.abc.Messageable]:
    """
    Wandelt einen ChannelSelect-Wert oder eine Kanal-ID
    in ein echtes Discord-Kanalobjekt um.
    """

    channel_id = getattr(raw_channel, "id", raw_channel)

    try:
        channel_id = int(channel_id)
    except (TypeError, ValueError):
        return None

    channel = bot.get_channel(channel_id)

    if channel is not None:
        return channel

    try:
        return await bot.fetch_channel(channel_id)
    except (
        discord.HTTPException,
        discord.NotFound,
        discord.Forbidden,
    ):
        return None


def has_announcement_permission(
    interaction: discord.Interaction,
) -> bool:
    if interaction.guild is None or interaction.channel is None:
        return False

    channel_permissions = interaction.channel.permissions_for(
        interaction.user
    )

    if not channel_permissions.view_channel:
        return False

    guild_permissions = interaction.user.guild_permissions

    if guild_permissions.administrator:
        return True

    if not REQUIRE_ADMINISTRATOR and guild_permissions.manage_guild:
        return True

    if ALLOWED_ROLE_IDS:
        user_role_ids = {
            role.id
            for role in getattr(interaction.user, "roles", [])
        }

        if user_role_ids & ALLOWED_ROLE_IDS:
            return True

    return False


# ============================================================
# BUTTON-DATEN
# ============================================================

class AnnouncementButton:
    def __init__(
        self,
        label: str = "",
        url: str = "",
        emoji: str = "",
    ):
        self.label = label.strip()
        self.url = url.strip()
        self.emoji = emoji.strip()

    def is_valid(self) -> bool:
        return (
            bool(self.label)
            and len(self.label) <= 80
            and valid_url(self.url)
        )

    def is_empty(self) -> bool:
        return not self.label and not self.url

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "url": self.url,
            "emoji": self.emoji,
        }


# ============================================================
# GIVEAWAY VIEW
# ============================================================

class GiveawayView(discord.ui.View):
    def __init__(
        self,
        cog: "Announcements",
        giveaway_id: str,
    ):
        super().__init__(timeout=None)

        self.cog = cog
        self.giveaway_id = giveaway_id

        button = discord.ui.Button(
            label="Teilnehmen",
            emoji="🎟️",
            style=discord.ButtonStyle.success,
            custom_id=f"giveaway_join:{giveaway_id}",
        )

        async def callback(interaction: discord.Interaction):
            await self.join_giveaway(interaction)

        button.callback = callback
        self.add_item(button)

    async def join_giveaway(
        self,
        interaction: discord.Interaction,
    ):
        giveaway = self.cog.giveaways.get(self.giveaway_id)

        if not giveaway:
            await interaction.response.send_message(
                "❌ Dieses Giveaway existiert nicht mehr.",
                ephemeral=True,
            )
            return

        if giveaway.get("ended"):
            await interaction.response.send_message(
                "❌ Dieses Giveaway ist bereits beendet.",
                ephemeral=True,
            )
            return

        end_at = string_to_datetime(giveaway["end_at"])

        if end_at <= utc_now():
            await interaction.response.send_message(
                "❌ Dieses Giveaway ist bereits beendet.",
                ephemeral=True,
            )
            return

        user_id = interaction.user.id

        participants = set(
            giveaway.get("participants", [])
        )

        if user_id in participants:
            participants.remove(user_id)
            giveaway["participants"] = list(participants)

            await self.cog.save_giveaways()

            await interaction.response.send_message(
                "↩️ Du wurdest aus dem Giveaway entfernt.",
                ephemeral=True,
            )

            await self.cog.update_giveaway_messages(giveaway)
            return

        participants.add(user_id)
        giveaway["participants"] = list(participants)

        await self.cog.save_giveaways()

        await interaction.response.send_message(
            "🎉 **Du nimmst jetzt am Giveaway teil!**\n\n"
            "Viel Glück! 🍀",
            ephemeral=True,
        )

        await self.cog.update_giveaway_messages(giveaway)


# ============================================================
# GIVEAWAY CLAIM VIEW (Gewinner-Ticket)
# ============================================================

class GiveawayClaimView(discord.ui.View):
    """
    Persönlicher Claim-Button, den nur EIN bestimmter Gewinner
    verwenden kann (per DM verschickt). Erstellt beim Klick ein
    privates Ticket im Claim-Kanal und deaktiviert sich danach
    für diesen Gewinner dauerhaft.
    """

    def __init__(
        self,
        cog: "Announcements",
        giveaway_id: str,
        winner_id: int,
        *,
        claimed: bool = False,
    ):
        super().__init__(timeout=None)

        self.cog = cog
        self.giveaway_id = giveaway_id
        self.winner_id = winner_id

        button = discord.ui.Button(
            label=(
                "Ticket bereits erstellt"
                if claimed
                else "Ticket öffnen"
            ),
            emoji="🎫",
            style=(
                discord.ButtonStyle.secondary
                if claimed
                else discord.ButtonStyle.success
            ),
            disabled=claimed,
            custom_id=f"giveaway_claim:{giveaway_id}:{winner_id}",
        )

        async def callback(interaction: discord.Interaction):
            await self.claim(interaction, button)

        button.callback = callback
        self.add_item(button)

    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.winner_id:
            await interaction.response.send_message(
                "❌ Dieser Button gehört nicht dir.",
                ephemeral=True,
            )
            return

        giveaway = self.cog.giveaways.get(self.giveaway_id)

        if giveaway is None:
            await interaction.response.send_message(
                "❌ Dieses Giveaway existiert nicht mehr.",
                ephemeral=True,
            )
            return

        claimed_by = set(giveaway.get("claimed_by", []))

        if self.winner_id in claimed_by:
            await interaction.response.send_message(
                "ℹ️ Du hast dein Ticket bereits erstellt.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        ticket_channel = await self.cog.create_giveaway_ticket(
            giveaway,
            interaction.user,
        )

        if ticket_channel is None:
            await interaction.followup.send(
                "❌ Dein Ticket konnte nicht automatisch erstellt "
                "werden. Bitte melde dich direkt beim Team.",
                ephemeral=True,
            )
            return

        claimed_by.add(self.winner_id)
        giveaway["claimed_by"] = list(claimed_by)

        await self.cog.save_giveaways()

        button.disabled = True
        button.label = "Ticket bereits erstellt"
        button.style = discord.ButtonStyle.secondary

        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        mention = getattr(
            ticket_channel,
            "mention",
            str(ticket_channel),
        )

        await interaction.followup.send(
            f"✅ **Dein Ticket wurde erstellt:** {mention}\n"
            "Unser Team meldet sich dort bei dir. 🎁",
            ephemeral=True,
        )


# ============================================================
# CHANNEL SELECT
# ============================================================

class AnnouncementChannelSelect(
    discord.ui.ChannelSelect
):
    def __init__(self, panel: "AnnouncementPanel"):
        self.panel = panel

        super().__init__(
            placeholder="📢 Zielkanäle auswählen...",
            min_values=1,
            max_values=25,
            # Zunächst nur normale Text-/News-Kanäle.
            # Dadurch werden Threads/Foren als Fehlerquelle
            # beim Sofortversand ausgeschlossen.
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news,
            ],
            custom_id="announcement_channel_select",
            row=2,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        self.panel.channels = list(self.values)

        await interaction.response.edit_message(
            content=None,
            embed=self.panel.make_panel_embed(),
            view=self.panel,
        )


# ============================================================
# KATEGORIE SELECT
# ============================================================

class CategorySelect(discord.ui.Select):
    def __init__(self, panel: "AnnouncementPanel"):
        self.panel = panel

        options = []

        for key, info in CATEGORY_INFO.items():
            options.append(
                discord.SelectOption(
                    label=info["name"][:100],
                    value=key,
                    emoji=info["emoji"],
                    description=(
                        f"Nur {info['name']} Templates"
                    ),
                    default=(key == panel.category),
                )
            )

        super().__init__(
            placeholder="📂 Kategorie auswählen...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="announcement_category_select",
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        self.panel.category = self.values[0]

        available = [
            key
            for key, template in TEMPLATES.items()
            if template["category"] == self.panel.category
        ]

        if available:
            self.panel.template_key = available[0]
            self.panel.load_template(available[0])

        self.panel.rebuild_selects()

        await interaction.response.edit_message(
            content=None,
            embed=self.panel.make_panel_embed(),
            view=self.panel,
        )


# ============================================================
# TEMPLATE SELECT
# ============================================================

class TemplateSelect(discord.ui.Select):
    def __init__(self, panel: "AnnouncementPanel"):
        self.panel = panel

        options = []

        for key, template in TEMPLATES.items():
            if template["category"] != panel.category:
                continue

            options.append(
                discord.SelectOption(
                    label=template["name"][:100],
                    value=key,
                    emoji=CATEGORY_INFO[
                        template["category"]
                    ]["emoji"],
                    description="Template verwenden",
                    default=(key == panel.template_key),
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="Keine Templates",
                    value="none",
                )
            )

        super().__init__(
            placeholder="🎨 Template auswählen...",
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id="announcement_template_select",
            row=1,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        key = self.values[0]

        if key == "none":
            await interaction.response.send_message(
                "❌ Für diese Kategorie gibt es keine Templates.",
                ephemeral=True,
            )
            return

        self.panel.template_key = key
        self.panel.load_template(key)
        self.panel.rebuild_selects()

        await interaction.response.edit_message(
            content=None,
            embed=self.panel.make_panel_embed(),
            view=self.panel,
        )


# ============================================================
# CONTENT MODAL
# ============================================================

class AnnouncementModal(discord.ui.Modal):
    def __init__(self, panel: "AnnouncementPanel"):
        super().__init__(title="Nachricht bearbeiten")

        self.panel = panel

        self.title_input = discord.ui.TextInput(
            label="Titel",
            placeholder="Titel deiner Nachricht",
            default=panel.title_text,
            max_length=256,
            required=True,
        )

        self.text_input = discord.ui.TextInput(
            label="Text",
            placeholder="Text deiner Nachricht...",
            default=panel.body_text,
            style=discord.TextStyle.paragraph,
            max_length=4000,
            required=True,
        )

        self.ping_input = discord.ui.TextInput(
            label="Ping",
            placeholder="@everyone, @here oder <@&ROLE_ID>",
            default=panel.ping,
            max_length=1000,
            required=False,
        )

        self.image_input = discord.ui.TextInput(
            label="Bild-URL",
            placeholder="https://example.com/image.png",
            default=panel.image_url or "",
            max_length=1000,
            required=False,
        )

        self.color_input = discord.ui.TextInput(
            label="Farbe",
            placeholder="blue / red / green / #5865F2",
            default="",
            max_length=30,
            required=False,
        )

        self.add_item(self.title_input)
        self.add_item(self.text_input)
        self.add_item(self.ping_input)
        self.add_item(self.image_input)
        self.add_item(self.color_input)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        image = self.image_input.value.strip()

        if image and not valid_url(image):
            await interaction.response.send_message(
                "❌ Die Bild-URL muss mit `http://` oder "
                "`https://` beginnen.",
                ephemeral=True,
            )
            return

        self.panel.title_text = self.title_input.value
        self.panel.body_text = self.text_input.value
        self.panel.ping = self.ping_input.value.strip()
        self.panel.image_url = image or None

        default_color = TEMPLATES[
            self.panel.template_key
        ]["color"]

        self.panel.color = parse_color(
            self.color_input.value,
            default_color,
        )

        await interaction.response.edit_message(
            content=None,
            embed=self.panel.make_panel_embed(),
            view=self.panel,
        )


# ============================================================
# BUTTON MODAL
# ============================================================

class ButtonModal(discord.ui.Modal):
    def __init__(
        self,
        panel: "AnnouncementPanel",
        index: int,
    ):
        super().__init__(
            title=f"Button {index + 1}"
        )

        self.panel = panel
        self.index = index

        current = panel.buttons[index]

        self.label_input = discord.ui.TextInput(
            label="Button-Text",
            placeholder=(
                "Website öffnen"
            ),
            default=current.label,
            max_length=80,
            required=False,
        )

        self.url_input = discord.ui.TextInput(
            label="URL",
            placeholder="https://example.com",
            default=current.url,
            max_length=1000,
            required=False,
        )

        self.emoji_input = discord.ui.TextInput(
            label="Emoji",
            placeholder="🌐 / 💬 / 🎫 / 🛒",
            default=current.emoji,
            max_length=60,
            required=False,
        )

        self.add_item(self.label_input)
        self.add_item(self.url_input)
        self.add_item(self.emoji_input)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        label = self.label_input.value.strip()
        url = self.url_input.value.strip()
        emoji = self.emoji_input.value.strip()

        if not label and not url:
            self.panel.buttons[
                self.index
            ] = AnnouncementButton()

            await interaction.response.edit_message(
                content=None,
                embed=self.panel.make_panel_embed(),
                view=self.panel,
            )
            return

        button = AnnouncementButton(
            label,
            url,
            emoji,
        )

        if not button.is_valid():
            await interaction.response.send_message(
                "❌ Ungültiger Button. Trage einen Text UND "
                "eine gültige `https://` URL ein.",
                ephemeral=True,
            )
            return

        self.panel.buttons[
            self.index
        ] = button

        await interaction.response.edit_message(
            content=None,
            embed=self.panel.make_panel_embed(),
            view=self.panel,
        )


# ============================================================
# BUTTON MANAGEMENT
# ============================================================

class ButtonManagementView(discord.ui.View):
    def __init__(
        self,
        panel: "AnnouncementPanel",
    ):
        super().__init__(timeout=180)

        self.panel = panel

        for index in range(5):
            current = panel.buttons[index]

            label = (
                current.label[:60]
                if not current.is_empty()
                else f"Button {index + 1} (leer)"
            )

            display_emoji = current.emoji or "🔗"

            try:
                button = discord.ui.Button(
                    label=label,
                    emoji=display_emoji,
                    style=(
                        discord.ButtonStyle.success
                        if current.is_valid()
                        else discord.ButtonStyle.secondary
                    ),
                )
            except (ValueError, TypeError):
                button = discord.ui.Button(
                    label=label,
                    emoji="🔗",
                    style=(
                        discord.ButtonStyle.success
                        if current.is_valid()
                        else discord.ButtonStyle.secondary
                    ),
                )

            async def callback(
                interaction: discord.Interaction,
                index=index,
            ):
                await interaction.response.send_modal(
                    ButtonModal(self.panel, index)
                )

            button.callback = callback
            self.add_item(button)


# ============================================================
# SCHEDULE MODAL
# ============================================================

class ScheduleModal(discord.ui.Modal):
    def __init__(self, panel: "AnnouncementPanel"):
        super().__init__(
            title="Nachricht planen"
        )

        self.panel = panel

        self.date_input = discord.ui.TextInput(
            label="Datum (JJJJ-MM-TT)",
            placeholder="2026-08-10",
            max_length=10,
            required=True,
        )

        self.time_input = discord.ui.TextInput(
            label="Uhrzeit UTC (HH:MM)",
            placeholder="18:30",
            max_length=5,
            required=True,
        )

        self.repeat_input = discord.ui.TextInput(
            label="Wiederholung",
            placeholder="none / hourly / daily / weekly",
            default="none",
            max_length=20,
            required=True,
        )

        self.add_item(self.date_input)
        self.add_item(self.time_input)
        self.add_item(self.repeat_input)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        try:
            scheduled = datetime.strptime(
                f"{self.date_input.value.strip()} "
                f"{self.time_input.value.strip()}",
                "%Y-%m-%d %H:%M",
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            await interaction.response.send_message(
                "❌ Ungültiges Datum/Uhrzeit-Format.",
                ephemeral=True,
            )
            return

        if scheduled <= utc_now():
            await interaction.response.send_message(
                "❌ Die geplante Zeit muss in der Zukunft liegen.",
                ephemeral=True,
            )
            return

        repeat = self.repeat_input.value.strip().lower()

        if repeat not in {
            "none",
            "hourly",
            "daily",
            "weekly",
        }:
            await interaction.response.send_message(
                "❌ Erlaubt: `none`, `hourly`, `daily`, `weekly`.",
                ephemeral=True,
            )
            return

        if not self.panel.channels:
            await interaction.response.send_message(
                "❌ Bitte zuerst mindestens einen Zielkanal auswählen.",
                ephemeral=True,
            )
            return

        schedule = {
            "id": str(
                int(utc_now().timestamp() * 1000)
            ),
            "created_by": interaction.user.id,
            "created_at": datetime_to_string(
                utc_now()
            ),
            "send_at": datetime_to_string(
                scheduled
            ),
            "repeat": repeat,
            "category": self.panel.category,
            "template_key": self.panel.template_key,
            "title": self.panel.title_text,
            "text": self.panel.body_text,
            "ping": self.panel.ping,
            "image_url": self.panel.image_url,
            "color": self.panel.color.value,
            "channels": [
                channel.id
                for channel in self.panel.channels
            ],
            "buttons": [
                button.to_dict()
                for button in self.panel.buttons
                if button.is_valid()
            ],
        }

        self.panel.cog.schedules.append(
            schedule
        )

        await self.panel.cog.save_schedules()

        timestamp = int(
            scheduled.timestamp()
        )

        await interaction.response.send_message(
            content=(
                "✅ **Nachricht erfolgreich geplant!**\n\n"
                f"⏰ **Zeitpunkt:** <t:{timestamp}:F>\n"
                f"🔁 **Wiederholung:** `{repeat}`\n"
                f"📢 **Kanäle:** "
                f"`{len(self.panel.channels)}`\n\n"
                "Das permanente Announcement-Panel bleibt bestehen."
            ),
            ephemeral=True,
        )


# ============================================================
# GIVEAWAY MODAL
# ============================================================

class GiveawayModal(discord.ui.Modal):
    def __init__(self, panel: "AnnouncementPanel"):
        super().__init__(
            title="🎁 Giveaway erstellen"
        )

        self.panel = panel

        self.prize_input = discord.ui.TextInput(
            label="Gewinn",
            placeholder="z. B. 20€ PayPal / Rang / Item",
            max_length=256,
            required=True,
        )

        self.winners_input = discord.ui.TextInput(
            label="Anzahl Gewinner",
            placeholder="1",
            default="1",
            max_length=3,
            required=True,
        )

        self.duration_input = discord.ui.TextInput(
            label="Dauer in Minuten",
            placeholder="60",
            default="60",
            max_length=6,
            required=True,
        )

        self.role_input = discord.ui.TextInput(
            label="Gewinner-Rollen-ID",
            placeholder="123456789012345678 oder leer",
            max_length=30,
            required=False,
        )

        self.text_input = discord.ui.TextInput(
            label="Text",
            placeholder="Text des Giveaways...",
            default=panel.body_text,
            style=discord.TextStyle.paragraph,
            max_length=3000,
            required=True,
        )

        self.add_item(self.prize_input)
        self.add_item(self.winners_input)
        self.add_item(self.duration_input)
        self.add_item(self.role_input)
        self.add_item(self.text_input)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        try:
            winners = int(
                self.winners_input.value.strip()
            )
            duration = int(
                self.duration_input.value.strip()
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Gewinner und Dauer müssen Zahlen sein.",
                ephemeral=True,
            )
            return

        if winners < 1 or winners > 50:
            await interaction.response.send_message(
                "❌ Die Gewinneranzahl muss zwischen 1 und 50 liegen.",
                ephemeral=True,
            )
            return

        if duration < 1 or duration > 43200:
            await interaction.response.send_message(
                "❌ Die Dauer muss zwischen 1 Minute "
                "und 30 Tagen liegen.",
                ephemeral=True,
            )
            return

        role_id = None
        role_text = self.role_input.value.strip()

        if role_text:
            try:
                role_id = int(role_text)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Die Rollen-ID muss eine Zahl sein.",
                    ephemeral=True,
                )
                return

            role = interaction.guild.get_role(
                role_id
            )

            if role is None:
                await interaction.response.send_message(
                    "❌ Diese Rolle wurde auf dem Server nicht gefunden.",
                    ephemeral=True,
                )
                return

        if not self.panel.channels:
            await interaction.response.send_message(
                "❌ Bitte zuerst mindestens einen Zielkanal auswählen.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        giveaway_id = str(
            int(utc_now().timestamp() * 1000)
        )

        end_at = (
            utc_now()
            + timedelta(minutes=duration)
        )

        giveaway = {
            "id": giveaway_id,
            "guild_id": interaction.guild.id,
            "created_by": interaction.user.id,
            "created_at": datetime_to_string(
                utc_now()
            ),
            "end_at": datetime_to_string(
                end_at
            ),
            "prize": self.prize_input.value.strip(),
            "winners": winners,
            "winner_role_id": role_id,
            "title": self.panel.title_text,
            "text": self.text_input.value,
            "color": self.panel.color.value,
            "image_url": self.panel.image_url,
            "ping": self.panel.ping,
            "channels": [
                channel.id
                for channel in self.panel.channels
            ],
            "messages": [],
            "participants": [],
            "claimed_by": [],
            "ended": False,
        }

        self.panel.cog.giveaways[
            giveaway_id
        ] = giveaway

        await self.panel.cog.save_giveaways()

        success = await self.panel.cog.publish_giveaway(
            giveaway
        )

        if not success:
            del self.panel.cog.giveaways[
                giveaway_id
            ]

            await self.panel.cog.save_giveaways()

            await interaction.followup.send(
                "❌ Das Giveaway konnte in keinen Zielkanal gesendet werden.",
                ephemeral=True,
            )
            return

        timestamp = int(
            end_at.timestamp()
        )

        await interaction.followup.send(
            content=(
                "🎁 **Giveaway erfolgreich erstellt!** ✨\n\n"
                f"🏆 **Gewinn:** {self.prize_input.value}\n"
                f"👑 **Gewinner:** {winners}\n"
                f"⏰ **Endet:** <t:{timestamp}:F> "
                f"(<t:{timestamp}:R>)\n"
                f"📢 **Kanäle:** "
                f"{len(self.panel.channels)}\n\n"
                "Das Giveaway läuft jetzt automatisch – Teilnehmerzahl "
                "und Countdown aktualisieren sich live. Gewinner "
                "bekommen nach Ablauf automatisch einen persönlichen "
                "Claim-Button per DM. 🎫"
            ),
            ephemeral=True,
        )


# ============================================================
# CONFIRM SEND
# ============================================================

class ConfirmSendView(discord.ui.View):
    def __init__(
        self,
        panel: "AnnouncementPanel",
    ):
        super().__init__(timeout=120)

        self.panel = panel

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        return self.panel.can_use(interaction)

    @discord.ui.button(
        label="Jetzt senden",
        emoji="✅",
        style=discord.ButtonStyle.success,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not self.panel.channels:
            await interaction.response.send_message(
                "❌ Kein Zielkanal ausgewählt.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        results = []

        for raw_channel in self.panel.channels:
            channel_id = getattr(
                raw_channel,
                "id",
                raw_channel,
            )

            try:
                channel = await resolve_channel(
                    self.panel.cog.bot,
                    channel_id,
                )

                if channel is None:
                    results.append(
                        f"❌ <#{channel_id}> – "
                        "Kanal konnte nicht gefunden werden."
                    )
                    continue

                await self.panel.cog.send_to_channel(
                    channel,
                    self.panel,
                )

                results.append(
                    f"✅ {getattr(channel, 'mention', f'<#{channel_id}>')} "
                    "– gesendet"
                )

            except discord.Forbidden:
                results.append(
                    f"❌ <#{channel_id}> – Discord verweigert "
                    "den Versand. Bitte Berechtigungen prüfen."
                )

            except discord.HTTPException as exc:
                results.append(
                    f"❌ <#{channel_id}> – Discord API Fehler "
                    f"`{exc.status}`: `{exc}`"
                )

            except Exception as exc:
                log.exception(
                    "[ANNOUNCE] Versandfehler in Kanal %s",
                    channel_id,
                )

                results.append(
                    f"❌ <#{channel_id}> – "
                    f"`{type(exc).__name__}: {exc}`"
                )

        await interaction.followup.send(
            content=(
                "📢 **Versand abgeschlossen.**\n\n"
                + "\n".join(results)
            ),
            ephemeral=True,
        )

        self.stop()

    @discord.ui.button(
        label="Abbrechen",
        emoji="❌",
        style=discord.ButtonStyle.danger,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.edit_message(
            content="❌ Versand abgebrochen.",
            embed=None,
            view=None,
        )

        self.stop()


# ============================================================
# SCHEDULE LIST
# ============================================================

class ScheduleView(discord.ui.View):
    def __init__(
        self,
        cog: "Announcements",
    ):
        super().__init__(timeout=180)

        self.add_item(
            ScheduleDeleteSelect(cog)
        )


class ScheduleDeleteSelect(discord.ui.Select):
    def __init__(
        self,
        cog: "Announcements",
    ):
        self.cog = cog

        options = []

        for schedule in cog.schedules[:25]:
            try:
                send_at = string_to_datetime(
                    schedule["send_at"]
                )

                description = (
                    f"{send_at.strftime('%d.%m.%Y %H:%M')} UTC"
                )
            except Exception:
                description = "Ungültige Planung"

            title_preview = (
                schedule.get("title", "")[:60]
                or "(kein Titel)"
            )

            options.append(
                discord.SelectOption(
                    label=title_preview[:100],
                    value=schedule["id"],
                    description=description[:100],
                    emoji="🗑️",
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="Keine geplanten Nachrichten",
                    value="none",
                )
            )

        super().__init__(
            placeholder="🗑️ Planung zum Löschen auswählen...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        selected = self.values[0]

        if selected == "none":
            await interaction.response.send_message(
                "ℹ️ Keine geplanten Nachrichten.",
                ephemeral=True,
            )
            return

        before = len(self.cog.schedules)

        self.cog.schedules = [
            schedule
            for schedule in self.cog.schedules
            if schedule["id"] != selected
        ]

        if len(self.cog.schedules) == before:
            await interaction.response.send_message(
                "❌ Planung nicht gefunden.",
                ephemeral=True,
            )
            return

        await self.cog.save_schedules()

        await interaction.response.edit_message(
            content="🗑️ **Planung gelöscht.**",
            view=None,
        )


# ============================================================
# HAUPTPANEL
# ============================================================

class AnnouncementPanel(discord.ui.View):
    def __init__(
        self,
        cog: "Announcements",
    ):
        super().__init__(timeout=None)

        self.cog = cog
        self.bot = cog.bot

        self.category = "ANNOUNCE"
        self.template_key = "announcement_1"

        self.channels: list = []

        template = TEMPLATES[
            self.template_key
        ]

        self.title_text = template["title"]
        self.body_text = template["text"]
        self.ping = template["ping"]
        self.image_url: str | None = None
        self.color = template["color"]

        self.buttons = [
            AnnouncementButton()
            for _ in range(5)
        ]

        self.category_select = CategorySelect(
            self
        )

        self.template_select = TemplateSelect(
            self
        )

        self.channel_select = (
            AnnouncementChannelSelect(self)
        )

        self.add_item(
            self.category_select
        )

        self.add_item(
            self.template_select
        )

        self.add_item(
            self.channel_select
        )

    # ========================================================
    # TEMPLATE
    # ========================================================

    def load_template(
        self,
        key: str,
    ):
        template = TEMPLATES[key]

        self.title_text = template["title"]
        self.body_text = template["text"]
        self.ping = template["ping"]
        self.color = template["color"]
        self.image_url = None

        self.buttons = [
            AnnouncementButton()
            for _ in range(5)
        ]

    def rebuild_selects(self):
        for item in (
            self.category_select,
            self.template_select,
        ):
            try:
                self.remove_item(item)
            except ValueError:
                pass

        self.category_select = CategorySelect(
            self
        )

        self.template_select = TemplateSelect(
            self
        )

        self.add_item(
            self.category_select
        )

        self.add_item(
            self.template_select
        )

    # ========================================================
    # PERMISSION
    # ========================================================

    def can_use(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        return has_announcement_permission(
            interaction
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if not self.can_use(interaction):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, dieses Panel "
                "zu benutzen.",
                ephemeral=True,
            )
            return False

        return True

    # ========================================================
    # ANNOUNCEMENT EMBED
    # ========================================================

    def make_announcement_embed(
        self,
    ) -> discord.Embed:
        return build_embed(
            title=self.title_text,
            text=self.body_text,
            color=self.color,
            author=self.bot.user,
            image_url=self.image_url,
        )

    # ========================================================
    # PANEL EMBED
    # ========================================================

    def make_panel_embed(
        self,
    ) -> discord.Embed:
        category = CATEGORY_INFO[
            self.category
        ]

        if self.channels:
            channel_text = ", ".join(
                getattr(
                    channel,
                    "mention",
                    str(channel),
                )
                for channel in self.channels
            )
        else:
            channel_text = (
                "*Keine Zielkanäle ausgewählt*"
            )

        buttons = [
            b
            for b in self.buttons
            if b.is_valid()
        ]

        embed = discord.Embed(
            title=PANEL_TITLE,
            description=(
                "Erstellt, plant und versendet hier eure "
                "Server-Nachrichten, Updates und Giveaways.\n\n"
                "**Ablauf:** 📂 Kategorie → 🎨 Template → "
                "📢 Kanäle → 📝 Inhalt → 🚀 Senden / Planen"
            ),
            color=self.color,
        )

        embed.add_field(
            name="📂 Kategorie",
            value=category["name"],
            inline=True,
        )

        embed.add_field(
            name="🎨 Template",
            value=truncate(
                TEMPLATES[
                    self.template_key
                ]["name"]
            ),
            inline=True,
        )

        embed.add_field(
            name="🔗 Buttons",
            value=f"{len(buttons)}/5 gesetzt",
            inline=True,
        )

        embed.add_field(
            name="📢 Zielkanäle",
            value=truncate(channel_text),
            inline=False,
        )

        embed.add_field(
            name="📣 Ping",
            value=truncate(
                self.ping
                or "*Kein Ping*"
            ),
            inline=True,
        )

        embed.add_field(
            name="\u200b",
            value="\u200b",
            inline=True,
        )

        embed.add_field(
            name="\u200b",
            value="\u200b",
            inline=True,
        )

        embed.add_field(
            name="📝 Titel-Vorschau",
            value=truncate(
                self.title_text
            ),
            inline=False,
        )

        embed.add_field(
            name="💬 Nachrichten-Vorschau",
            value=truncate(
                self.body_text,
                512,
            ),
            inline=False,
        )

        if self.image_url:
            embed.set_image(
                url=self.image_url
            )

        if (
            self.bot.user
            and self.bot.user.display_avatar
        ):
            embed.set_thumbnail(
                url=self.bot.user.display_avatar.url
            )

        embed.set_footer(
            text=(
                "Announcement Control Center • "
                "Permanentes Panel"
            )
        )

        return embed

    # ========================================================
    # CONTENT
    # ========================================================

    @discord.ui.button(
        label="Inhalt",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="announcement_edit_content",
        row=3,
    )
    async def edit_content(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.send_modal(
            AnnouncementModal(self)
        )

    # ========================================================
    # BUTTONS
    # ========================================================

    @discord.ui.button(
        label="Buttons",
        emoji="🔗",
        style=discord.ButtonStyle.secondary,
        custom_id="announcement_manage_buttons",
        row=3,
    )
    async def manage_buttons(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.send_message(
            "🔗 **Buttons konfigurieren**\n"
            "-# Klicke einen Button, um ihn zu bearbeiten.",
            view=ButtonManagementView(self),
            ephemeral=True,
        )

    # ========================================================
    # PREVIEW
    # ========================================================

    @discord.ui.button(
        label="Vorschau",
        emoji="👀",
        style=discord.ButtonStyle.secondary,
        custom_id="announcement_preview",
        row=3,
    )
    async def preview(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        embed = self.make_announcement_embed()

        buttons = [
            b.to_dict()
            for b in self.buttons
            if b.is_valid()
        ]

        view = make_button_view(buttons)

        await interaction.response.send_message(
            content=self.ping or None,
            embed=embed,
            view=view,
            ephemeral=True,
        )

    # ========================================================
    # SEND
    # ========================================================

    @discord.ui.button(
        label="Senden",
        emoji="🚀",
        style=discord.ButtonStyle.success,
        custom_id="announcement_send",
        row=3,
    )
    async def send(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not self.channels:
            await interaction.response.send_message(
                "❌ Bitte zuerst mindestens einen Zielkanal "
                "auswählen.",
                ephemeral=True,
            )
            return

        channel_text = ", ".join(
            getattr(
                channel,
                "mention",
                str(channel),
            )
            for channel in self.channels
        )

        await interaction.response.send_message(
            content=(
                "⚠️ **Versand bestätigen**\n\n"
                f"📂 {CATEGORY_INFO[self.category]['name']}\n"
                f"🎨 {TEMPLATES[self.template_key]['name']}\n"
                f"📢 Zielkanäle: "
                f"{truncate(channel_text, 500)}\n\n"
                "Soll die Nachricht jetzt gesendet werden?"
            ),
            embed=self.make_announcement_embed(),
            view=ConfirmSendView(self),
            ephemeral=True,
        )

    # ========================================================
    # PLANEN
    # ========================================================

    @discord.ui.button(
        label="Planen",
        emoji="🕐",
        style=discord.ButtonStyle.primary,
        custom_id="announcement_schedule",
        row=4,
    )
    async def schedule(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not self.channels:
            await interaction.response.send_message(
                "❌ Bitte zuerst mindestens einen Zielkanal "
                "auswählen.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            ScheduleModal(self)
        )

    # ========================================================
    # GEPLANT
    # ========================================================

    @discord.ui.button(
        label="Geplant",
        emoji="📅",
        style=discord.ButtonStyle.secondary,
        custom_id="announcement_scheduled",
        row=4,
    )
    async def scheduled(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not self.cog.schedules:
            await interaction.response.send_message(
                "📅 Keine Nachrichten geplant.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "📅 **Geplante Nachrichten**",
            view=ScheduleView(self.cog),
            ephemeral=True,
        )

    # ========================================================
    # GIVEAWAY
    # ========================================================

    @discord.ui.button(
        label="Giveaway",
        emoji="🎁",
        style=discord.ButtonStyle.success,
        custom_id="announcement_giveaway",
        row=4,
    )
    async def giveaway(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not self.channels:
            await interaction.response.send_message(
                "❌ Bitte zuerst mindestens einen Zielkanal "
                "auswählen.",
                ephemeral=True,
            )
            return

        self.category = "GIVEAWAY"

        available = [
            key
            for key, template in TEMPLATES.items()
            if template["category"] == "GIVEAWAY"
        ]

        if available:
            self.template_key = available[0]
            self.load_template(
                self.template_key
            )
            self.rebuild_selects()

        await interaction.response.send_modal(
            GiveawayModal(self)
        )

    # ========================================================
    # RESET
    # ========================================================

    @discord.ui.button(
        label="Reset",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="announcement_reset",
        row=4,
    )
    async def reset(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.category = "ANNOUNCE"
        self.template_key = "announcement_1"
        self.channels = []

        self.load_template(
            self.template_key
        )

        self.rebuild_selects()

        await interaction.response.edit_message(
            content=None,
            embed=self.make_panel_embed(),
            view=self,
        )


# ============================================================
# COG
# ============================================================

class Announcements(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

        self.schedules: list[dict] = []
        self.giveaways: dict[str, dict] = {}

        self.panel_message_id: int | None = None

        self._giveaway_views: dict[
            str,
            GiveawayView,
        ] = {}

        self._claim_views: dict[
            str,
            GiveawayClaimView,
        ] = {}

    # ========================================================
    # COG LOAD
    # ========================================================

    async def cog_load(self):
        ensure_data_directory()

        await self.load_schedules()
        await self.load_giveaways()

        if not self.scheduler.is_running():
            self.scheduler.start()

        if not self.giveaway_scheduler.is_running():
            self.giveaway_scheduler.start()

        self.bot.loop.create_task(
            self.initialize_panel()
        )

        self.bot.loop.create_task(
            self.restore_giveaway_views()
        )

        self.bot.loop.create_task(
            self.restore_claim_views()
        )

    # ========================================================
    # COG UNLOAD
    # ========================================================

    def cog_unload(self):
        self.scheduler.cancel()
        self.giveaway_scheduler.cancel()

    # ========================================================
    # SCHEDULE STORAGE
    # ========================================================

    async def load_schedules(self):
        ensure_data_directory()

        if not SCHEDULE_FILE.exists():
            self.schedules = []
            return

        try:
            with open(
                SCHEDULE_FILE,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            self.schedules = (
                data
                if isinstance(data, list)
                else []
            )

        except Exception:
            log.exception(
                "[ANNOUNCE] Schedules konnten nicht geladen werden."
            )
            self.schedules = []

    async def save_schedules(self):
        ensure_data_directory()

        temporary = SCHEDULE_FILE.with_suffix(
            ".tmp"
        )

        with open(
            temporary,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.schedules,
                file,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(
            temporary,
            SCHEDULE_FILE,
        )

    # ========================================================
    # GIVEAWAY STORAGE
    # ========================================================

    async def load_giveaways(self):
        ensure_data_directory()

        if not GIVEAWAY_FILE.exists():
            self.giveaways = {}
            return

        try:
            with open(
                GIVEAWAY_FILE,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            self.giveaways = (
                data
                if isinstance(data, dict)
                else {}
            )

        except Exception:
            log.exception(
                "[GIVEAWAY] Giveaways konnten nicht geladen werden."
            )
            self.giveaways = {}

    async def save_giveaways(self):
        ensure_data_directory()

        temporary = GIVEAWAY_FILE.with_suffix(
            ".tmp"
        )

        with open(
            temporary,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.giveaways,
                file,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(
            temporary,
            GIVEAWAY_FILE,
        )

    # ========================================================
    # PERMANENT PANEL
    # ========================================================

    async def initialize_panel(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)

        try:
            self.bot.add_view(
                AnnouncementPanel(self)
            )
        except Exception:
            log.exception(
                "[ANNOUNCE] Panel-View konnte nicht global "
                "registriert werden."
            )

        try:
            await self.ensure_panel()
        except Exception:
            log.exception(
                "[ANNOUNCE] Panel konnte nicht initialisiert werden."
            )

    async def lock_panel_channel(
        self,
        channel,
    ):
        if not LOCK_PANEL_CHANNEL:
            return

        guild = getattr(
            channel,
            "guild",
            None,
        )

        if guild is None:
            return

        try:
            current = channel.overwrites_for(
                guild.default_role
            )

            current.send_messages = False
            current.create_public_threads = False
            current.create_private_threads = False
            current.send_messages_in_threads = False

            await channel.set_permissions(
                guild.default_role,
                overwrite=current,
                reason=(
                    "Announcement Panel: Nur Administratoren "
                    "dürfen hier schreiben."
                ),
            )

        except discord.Forbidden:
            log.warning(
                "[ANNOUNCE] Keine Berechtigung, um den Panel-Kanal "
                "zu sperren."
            )

        except discord.HTTPException:
            log.exception(
                "[ANNOUNCE] Panel-Kanal konnte nicht gesperrt werden."
            )

    async def ensure_panel(self):
        channel = self.bot.get_channel(
            ANNOUNCEMENT_PANEL_CHANNEL_ID
        )

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    ANNOUNCEMENT_PANEL_CHANNEL_ID
                )
            except discord.HTTPException:
                log.exception(
                    "[ANNOUNCE] Panel-Kanal konnte nicht geladen werden."
                )
                return

        if not hasattr(
            channel,
            "fetch_message",
        ):
            log.error(
                "[ANNOUNCE] Panel-Kanal unterstützt keine Nachrichten."
            )
            return

        await self.lock_panel_channel(
            channel
        )

        panel = AnnouncementPanel(self)

        message = None

        if self.panel_message_id:
            try:
                message = await channel.fetch_message(
                    self.panel_message_id
                )
            except discord.HTTPException:
                message = None

        if message is None:
            try:
                async for candidate in channel.history(
                    limit=100
                ):
                    if (
                        candidate.author.id
                        == self.bot.user.id
                        and candidate.embeds
                        and candidate.embeds[0].title
                        == PANEL_TITLE
                    ):
                        message = candidate
                        break
            except discord.HTTPException:
                pass

        if message is None:
            message = await channel.send(
                embed=panel.make_panel_embed(),
                view=panel,
            )

            log.info(
                "[ANNOUNCE] Neues Panel erstellt: %s",
                message.id,
            )
        else:
            try:
                await message.edit(
                    embed=panel.make_panel_embed(),
                    view=panel,
                )

                log.info(
                    "[ANNOUNCE] Vorhandenes Panel aktualisiert: %s",
                    message.id,
                )

            except discord.HTTPException:
                log.exception(
                    "[ANNOUNCE] Panel konnte nicht bearbeitet werden."
                )

        self.panel_message_id = message.id

    # ========================================================
    # SEND CHANNEL
    # ========================================================

    async def send_to_channel(
        self,
        raw_channel,
        panel: AnnouncementPanel,
    ):
        """
        Zentraler Versand.

        Prüft zuerst:
        - Kanalauflösung
        - Guild
        - Bot-Mitglied
        - Send Messages
        - Embed Links

        Danach wird tatsächlich gesendet.
        """

        channel_id = getattr(
            raw_channel,
            "id",
            raw_channel,
        )

        channel = await resolve_channel(
            self.bot,
            channel_id,
        )

        if channel is None:
            raise RuntimeError(
                f"Kanal {channel_id} konnte nicht aufgelöst werden."
            )

        guild = getattr(
            channel,
            "guild",
            None,
        )

        if guild is None:
            raise RuntimeError(
                f"Kanal {channel_id} gehört zu keinem Server."
            )

        bot_member = guild.me

        if bot_member is None:
            try:
                bot_member = await guild.fetch_member(
                    self.bot.user.id
                )
            except Exception as exc:
                raise RuntimeError(
                    "Bot-Mitglied konnte nicht ermittelt werden."
                ) from exc

        permissions = channel.permissions_for(
            bot_member
        )

        # ----------------------------------------------------
        # TEXT / NEWS
        # ----------------------------------------------------

        if isinstance(
            channel,
            discord.TextChannel,
        ):
            if not permissions.send_messages:
                raise RuntimeError(
                    f"Bot hat in {channel.mention} "
                    "keine Berechtigung `Send Messages`."
                )

            if not permissions.embed_links:
                raise RuntimeError(
                    f"Bot hat in {channel.mention} "
                    "keine Berechtigung `Embed Links`."
                )

        # ----------------------------------------------------
        # THREAD
        # ----------------------------------------------------

        elif isinstance(
            channel,
            discord.Thread,
        ):
            if not permissions.send_messages:
                raise RuntimeError(
                    f"Bot kann in {channel.mention} "
                    "keine Nachrichten senden."
                )

            if not permissions.embed_links:
                raise RuntimeError(
                    f"Bot hat in {channel.mention} "
                    "keine Berechtigung `Embed Links`."
                )

        # ----------------------------------------------------
        # FORUM
        # ----------------------------------------------------

        elif isinstance(
            channel,
            discord.ForumChannel,
        ):
            if not permissions.send_messages:
                raise RuntimeError(
                    f"Bot hat in {channel.mention} "
                    "keine Berechtigung `Send Messages`."
                )

            if not permissions.embed_links:
                raise RuntimeError(
                    f"Bot hat in {channel.mention} "
                    "keine Berechtigung `Embed Links`."
                )

        else:
            raise RuntimeError(
                f"Nicht unterstützter Kanaltyp: "
                f"{type(channel).__name__}"
            )

        # ----------------------------------------------------
        # MESSAGE
        # ----------------------------------------------------

        embed = panel.make_announcement_embed()

        buttons = [
            button.to_dict()
            for button in panel.buttons
            if button.is_valid()
        ]

        view = make_button_view(
            buttons
        )

        content = panel.ping or None

        try:
            if isinstance(
                channel,
                discord.ForumChannel,
            ):
                await channel.create_thread(
                    name=panel.title_text[:100],
                    content=content,
                    embed=embed,
                    view=view,
                )

            elif isinstance(
                channel,
                (
                    discord.TextChannel,
                    discord.Thread,
                ),
            ):
                await channel.send(
                    content=content,
                    embed=embed,
                    view=view,
                )

            else:
                raise RuntimeError(
                    f"Kanal {channel.id} unterstützt keinen Versand."
                )

        except discord.Forbidden as exc:
            raise RuntimeError(
                f"Discord verweigert den Versand in "
                f"{getattr(channel, 'mention', channel.id)}. "
                "Prüfe `Send Messages`, `Embed Links` und "
                "bei Threads `Send Messages in Threads`."
            ) from exc

        except discord.HTTPException as exc:
            raise RuntimeError(
                f"Discord API Fehler in "
                f"{getattr(channel, 'mention', channel.id)}: "
                f"{exc.status} – {exc}"
            ) from exc

    # ========================================================
    # SCHEDULE SEND
    # ========================================================

    async def send_schedule(
        self,
        schedule: dict,
    ) -> bool:
        successful = 0
        failed = 0

        for channel_id in schedule.get(
            "channels",
            [],
        ):
            try:
                channel = await resolve_channel(
                    self.bot,
                    channel_id,
                )

                if channel is None:
                    raise RuntimeError(
                        "Kanal konnte nicht aufgelöst werden."
                    )

                embed = discord.Embed(
                    title=schedule["title"],
                    description=schedule["text"],
                    color=discord.Color(
                        schedule.get(
                            "color",
                            discord.Color.blurple().value,
                        )
                    ),
                    timestamp=utc_now(),
                )

                image_url = schedule.get(
                    "image_url"
                )

                if image_url:
                    embed.set_image(
                        url=image_url
                    )

                view = make_button_view(
                    schedule.get(
                        "buttons",
                        [],
                    )
                )

                content = (
                    schedule.get("ping")
                    or None
                )

                if isinstance(
                    channel,
                    (
                        discord.TextChannel,
                        discord.Thread,
                    ),
                ):
                    await channel.send(
                        content=content,
                        embed=embed,
                        view=view,
                    )

                elif isinstance(
                    channel,
                    discord.ForumChannel,
                ):
                    await channel.create_thread(
                        name=schedule["title"][:100],
                        content=content,
                        embed=embed,
                        view=view,
                    )

                else:
                    raise RuntimeError(
                        "Nicht unterstützter Kanaltyp."
                    )

                successful += 1

                log.info(
                    "[ANNOUNCE] Schedule %s erfolgreich in %s gesendet.",
                    schedule["id"],
                    channel_id,
                )

            except discord.Forbidden:
                failed += 1

                log.error(
                    "[ANNOUNCE] Keine Berechtigung für %s.",
                    channel_id,
                )

            except discord.HTTPException as exc:
                failed += 1

                log.error(
                    "[ANNOUNCE] Discord-Fehler %s: %s",
                    channel_id,
                    exc,
                )

            except Exception:
                failed += 1

                log.exception(
                    "[ANNOUNCE] Fehler bei Schedule %s.",
                    schedule["id"],
                )

        log.info(
            "[ANNOUNCE] Schedule %s abgeschlossen: "
            "%s erfolgreich / %s fehlgeschlagen.",
            schedule["id"],
            successful,
            failed,
        )

        return successful > 0

    # ========================================================
    # SCHEDULER
    # ========================================================

    @tasks.loop(seconds=15)
    async def scheduler(self):
        if not self.schedules:
            return

        now = utc_now()
        changed = False

        for schedule in list(
            self.schedules
        ):
            try:
                send_at = string_to_datetime(
                    schedule["send_at"]
                )
            except Exception:
                log.exception(
                    "[ANNOUNCE] Ungültige Planung %s.",
                    schedule.get("id"),
                )
                continue

            if send_at > now:
                continue

            success = await self.send_schedule(
                schedule
            )

            if not success:
                log.warning(
                    "[ANNOUNCE] Planung %s konnte nicht gesendet werden.",
                    schedule["id"],
                )
                continue

            repeat = schedule.get(
                "repeat",
                "none",
            )

            if repeat == "none":
                self.schedules.remove(
                    schedule
                )
                changed = True
                continue

            if repeat == "hourly":
                delta = timedelta(hours=1)
            elif repeat == "daily":
                delta = timedelta(days=1)
            elif repeat == "weekly":
                delta = timedelta(weeks=1)
            else:
                self.schedules.remove(
                    schedule
                )
                changed = True
                continue

            next_time = send_at + delta

            while next_time <= now:
                next_time += delta

            schedule["send_at"] = (
                datetime_to_string(
                    next_time
                )
            )

            changed = True

        if changed:
            await self.save_schedules()

    @scheduler.before_loop
    async def before_scheduler(self):
        await self.bot.wait_until_ready()

    # ========================================================
    # GIVEAWAY VIEW REGISTRATION
    # ========================================================

    def register_giveaway_view(
        self,
        giveaway_id: str,
    ) -> GiveawayView:
        existing = self._giveaway_views.get(
            giveaway_id
        )

        if existing is not None:
            return existing

        view = GiveawayView(
            self,
            giveaway_id,
        )

        self._giveaway_views[
            giveaway_id
        ] = view

        try:
            self.bot.add_view(view)
        except Exception:
            log.exception(
                "[GIVEAWAY] View konnte nicht registriert werden."
            )

        return view

    async def restore_giveaway_views(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)

        for giveaway_id, giveaway in list(
            self.giveaways.items()
        ):
            if giveaway.get("ended"):
                continue

            try:
                end_at = string_to_datetime(
                    giveaway["end_at"]
                )

                if end_at <= utc_now():
                    continue

                self.register_giveaway_view(
                    giveaway_id
                )

            except Exception:
                log.exception(
                    "[GIVEAWAY] View %s konnte nicht wiederhergestellt werden.",
                    giveaway_id,
                )

    # ========================================================
    # GIVEAWAY CLAIM VIEW REGISTRATION
    # ========================================================

    def register_claim_view(
        self,
        giveaway_id: str,
        winner_id: int,
        *,
        claimed: bool = False,
    ) -> GiveawayClaimView:
        key = f"{giveaway_id}:{winner_id}"

        existing = self._claim_views.get(key)

        if existing is not None:
            return existing

        view = GiveawayClaimView(
            self,
            giveaway_id,
            winner_id,
            claimed=claimed,
        )

        self._claim_views[key] = view

        try:
            self.bot.add_view(view)
        except Exception:
            log.exception(
                "[GIVEAWAY] Claim-View konnte nicht registriert werden."
            )

        return view

    async def restore_claim_views(self):
        """
        Stellt nach einem Bot-Neustart alle noch offenen
        Gewinner-Claim-Buttons wieder her, damit sie weiter
        funktionieren.
        """
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)

        for giveaway_id, giveaway in list(
            self.giveaways.items()
        ):
            if not giveaway.get("ended"):
                continue

            winner_ids = giveaway.get(
                "winner_ids",
                [],
            )

            claimed_by = set(
                giveaway.get(
                    "claimed_by",
                    [],
                )
            )

            for winner_id in winner_ids:
                try:
                    self.register_claim_view(
                        giveaway_id,
                        winner_id,
                        claimed=(
                            winner_id in claimed_by
                        ),
                    )
                except Exception:
                    log.exception(
                        "[GIVEAWAY] Claim-View für %s/%s konnte "
                        "nicht wiederhergestellt werden.",
                        giveaway_id,
                        winner_id,
                    )

    # ========================================================
    # GIVEAWAY EMBED
    # ========================================================

    def make_giveaway_embed(
        self,
        giveaway: dict,
    ) -> discord.Embed:
        end_at = string_to_datetime(
            giveaway["end_at"]
        )

        participants = len(
            giveaway.get(
                "participants",
                [],
            )
        )

        ended = giveaway.get("ended", False)

        color = discord.Color(
            giveaway.get(
                "color",
                discord.Color.green().value,
            )
        )

        embed = discord.Embed(
            title=f"🎁 {giveaway['title']}",
            description=(
                f"{DIVIDER}\n"
                f"{giveaway['text']}\n"
                f"{DIVIDER}"
            ),
            color=color,
        )

        embed.add_field(
            name="🏆 Gewinn",
            value=truncate(
                f"**{giveaway['prize']}**",
                1024,
            ),
            inline=True,
        )

        embed.add_field(
            name="👑 Gewinner",
            value=f"**{giveaway['winners']}**",
            inline=True,
        )

        embed.add_field(
            name="👥 Teilnehmer",
            value=f"**{participants}**",
            inline=True,
        )

        embed.add_field(
            name="⏰ Endet",
            value=(
                f"<t:{int(end_at.timestamp())}:F>\n"
                f"<t:{int(end_at.timestamp())}:R>"
            ),
            inline=False,
        )

        if not ended:
            created_at_raw = giveaway.get(
                "created_at"
            )

            if created_at_raw:
                try:
                    created_at = string_to_datetime(
                        created_at_raw
                    )

                    embed.add_field(
                        name="⏳ Fortschritt",
                        value=make_progress_bar(
                            created_at,
                            end_at,
                        ),
                        inline=False,
                    )
                except Exception:
                    pass

        embed.set_footer(
            text=(
                f"Giveaway ID: {giveaway['id']} • "
                + (
                    "Beendet"
                    if ended
                    else "Klicke auf 🎟️ Teilnehmen, um mitzumachen"
                )
            )
        )

        image_url = giveaway.get(
            "image_url"
        )

        if image_url:
            embed.set_image(
                url=image_url
            )

        return embed

    async def update_giveaway_messages(
        self,
        giveaway: dict,
    ) -> None:
        """
        Aktualisiert alle bereits gesendeten Giveaway-Nachrichten
        (in allen Zielkanälen) live, z. B. wenn sich die
        Teilnehmerzahl ändert.
        """
        embed = self.make_giveaway_embed(
            giveaway
        )

        for message_data in giveaway.get(
            "messages",
            [],
        ):
            try:
                channel = await resolve_channel(
                    self.bot,
                    message_data["channel_id"],
                )

                if channel is None:
                    continue

                message = await channel.fetch_message(
                    message_data["message_id"]
                )

                await message.edit(embed=embed)

            except Exception:
                log.exception(
                    "[GIVEAWAY] Live-Update fehlgeschlagen für "
                    "Nachricht %s.",
                    message_data.get("message_id"),
                )

    # ========================================================
    # PUBLISH GIVEAWAY
    # ========================================================

    async def publish_giveaway(
        self,
        giveaway: dict,
    ) -> bool:
        successful = 0

        giveaway_view = (
            self.register_giveaway_view(
                giveaway["id"]
            )
        )

        for channel_id in giveaway.get(
            "channels",
            [],
        ):
            try:
                channel = await resolve_channel(
                    self.bot,
                    channel_id,
                )

                if channel is None:
                    raise RuntimeError(
                        "Kanal konnte nicht aufgelöst werden."
                    )

                embed = self.make_giveaway_embed(
                    giveaway
                )

                content = (
                    giveaway.get("ping")
                    or None
                )

                if isinstance(
                    channel,
                    (
                        discord.TextChannel,
                        discord.Thread,
                    ),
                ):
                    message = await channel.send(
                        content=content,
                        embed=embed,
                        view=giveaway_view,
                    )

                    giveaway.setdefault(
                        "messages",
                        [],
                    ).append(
                        {
                            "channel_id": channel.id,
                            "message_id": message.id,
                        }
                    )

                    successful += 1

                elif isinstance(
                    channel,
                    discord.ForumChannel,
                ):
                    thread_with_message = (
                        await channel.create_thread(
                            name=giveaway["title"][:100],
                            content=content,
                            embed=embed,
                            view=giveaway_view,
                        )
                    )

                    message = (
                        thread_with_message.message
                    )

                    giveaway.setdefault(
                        "messages",
                        [],
                    ).append(
                        {
                            "channel_id": channel.id,
                            "message_id": message.id,
                        }
                    )

                    successful += 1

            except Exception:
                log.exception(
                    "[GIVEAWAY] Fehler beim Erstellen in %s.",
                    channel_id,
                )

        await self.save_giveaways()

        return successful > 0

    # ========================================================
    # GIVEAWAY CLAIM TICKET ERSTELLEN
    # ========================================================

    async def create_giveaway_ticket(
        self,
        giveaway: dict,
        winner: discord.abc.User,
    ) -> Optional[discord.abc.GuildChannel]:
        """
        Erstellt ein privates Ticket (Thread) im Claim-Kanal,
        sichtbar nur für den Gewinner und das Team.
        """
        channel = await resolve_channel(
            self.bot,
            GIVEAWAY_CLAIM_CHANNEL_ID,
        )

        if channel is None:
            log.error(
                "[GIVEAWAY] Claim-Kanal %s konnte nicht "
                "aufgelöst werden.",
                GIVEAWAY_CLAIM_CHANNEL_ID,
            )
            return None

        guild = self.bot.get_guild(
            giveaway["guild_id"]
        )

        guild_member = None

        if guild is not None:
            guild_member = guild.get_member(
                winner.id
            )

            if guild_member is None:
                try:
                    guild_member = await guild.fetch_member(
                        winner.id
                    )
                except Exception:
                    guild_member = None

        display_name = getattr(
            guild_member,
            "display_name",
            None,
        ) or str(winner)

        embed = discord.Embed(
            title="🎫 Giveaway-Gewinn einlösen",
            description=(
                f"{DIVIDER}\n"
                f"Herzlichen Glückwunsch, {winner.mention}! 🎉\n"
                f"{DIVIDER}\n\n"
                f"🎁 **Gewinn:** {giveaway['prize']}\n"
                f"🆔 **Giveaway-ID:** `{giveaway['id']}`\n\n"
                "Unser Team meldet sich hier bei dir, um deinen "
                "Gewinn zu übergeben. Bitte habt etwas Geduld. 💌"
            ),
            color=discord.Color.gold(),
        )

        thread_name = truncate(
            f"🎁 Giveaway-Ticket – {display_name}",
            100,
        )

        try:
            if isinstance(
                channel,
                discord.ForumChannel,
            ):
                thread_with_message = (
                    await channel.create_thread(
                        name=thread_name,
                        content=winner.mention,
                        embed=embed,
                    )
                )

                thread = thread_with_message.thread

                if guild_member is not None:
                    try:
                        await thread.add_user(
                            guild_member
                        )
                    except Exception:
                        pass

                return thread

            if isinstance(
                channel,
                discord.TextChannel,
            ):
                thread = None

                try:
                    thread = await channel.create_thread(
                        name=thread_name,
                        type=discord.ChannelType.private_thread,
                        invitable=False,
                        reason="Giveaway-Gewinn Claim-Ticket",
                    )
                except discord.HTTPException:
                    # Private Threads evtl. nicht verfügbar
                    # (z. B. fehlendes Community-Feature) ->
                    # Fallback auf öffentlichen Thread.
                    thread = await channel.create_thread(
                        name=thread_name,
                        type=discord.ChannelType.public_thread,
                        reason="Giveaway-Gewinn Claim-Ticket",
                    )

                await thread.send(
                    content=winner.mention,
                    embed=embed,
                )

                if guild_member is not None:
                    try:
                        await thread.add_user(
                            guild_member
                        )
                    except Exception:
                        pass

                return thread

            log.error(
                "[GIVEAWAY] Claim-Kanal %s hat einen nicht "
                "unterstützten Typ: %s",
                GIVEAWAY_CLAIM_CHANNEL_ID,
                type(channel).__name__,
            )
            return None

        except Exception:
            log.exception(
                "[GIVEAWAY] Ticket-Erstellung für %s fehlgeschlagen.",
                winner.id,
            )
            return None

    # ========================================================
    # GIVEAWAY END
    # ========================================================

    async def finish_giveaway(
        self,
        giveaway: dict,
    ):
        if giveaway.get("ended"):
            return

        giveaway["ended"] = True

        participants = list(
            set(
                giveaway.get(
                    "participants",
                    [],
                )
            )
        )

        winners_count = min(
            giveaway.get("winners", 1),
            len(participants),
        )

        winners = []

        if winners_count > 0:
            winners = secrets.SystemRandom().sample(
                participants,
                winners_count,
            )

        giveaway["winner_ids"] = winners
        giveaway.setdefault("claimed_by", [])

        guild = self.bot.get_guild(
            giveaway["guild_id"]
        )

        winner_mentions = []
        dm_sent_count = 0
        auto_ticket_count = 0

        if guild:
            role_id = giveaway.get(
                "winner_role_id"
            )

            role = (
                guild.get_role(role_id)
                if role_id
                else None
            )

            for user_id in winners:
                member = guild.get_member(
                    user_id
                )

                if member is None:
                    try:
                        member = await guild.fetch_member(
                            user_id
                        )
                    except Exception:
                        member = None

                if not member:
                    continue

                winner_mentions.append(
                    member.mention
                )

                if role:
                    try:
                        await member.add_roles(
                            role,
                            reason="Giveaway winner",
                        )
                    except discord.Forbidden:
                        log.warning(
                            "[GIVEAWAY] Rolle konnte %s nicht "
                            "vergeben werden.",
                            member.id,
                        )

                # ------------------------------------------------
                # PERSÖNLICHEN CLAIM-BUTTON PER DM VERSCHICKEN
                # ------------------------------------------------

                claim_view = self.register_claim_view(
                    giveaway["id"],
                    user_id,
                )

                dm_embed = discord.Embed(
                    title="🎉 Du hast gewonnen!",
                    description=(
                        f"{DIVIDER}\n"
                        f"Herzlichen Glückwunsch! Du hast beim "
                        f"Giveaway **{giveaway['title']}** "
                        f"gewonnen! 🎁\n"
                        f"{DIVIDER}\n\n"
                        f"🏆 **Gewinn:** {giveaway['prize']}\n\n"
                        "Klicke unten auf den Button, um dein "
                        "persönliches Ticket zu öffnen und deinen "
                        "Gewinn abzuholen. Nur du kannst diesen "
                        "Button benutzen. 🎫"
                    ),
                    color=discord.Color.gold(),
                )

                try:
                    await member.send(
                        embed=dm_embed,
                        view=claim_view,
                    )
                    dm_sent_count += 1

                except discord.Forbidden:
                    # DMs geschlossen -> Ticket automatisch
                    # erstellen, damit der Gewinn nicht verloren
                    # geht.
                    ticket = await self.create_giveaway_ticket(
                        giveaway,
                        member,
                    )

                    if ticket is not None:
                        claimed = set(
                            giveaway.get(
                                "claimed_by",
                                [],
                            )
                        )
                        claimed.add(user_id)
                        giveaway["claimed_by"] = list(
                            claimed
                        )
                        auto_ticket_count += 1

                except Exception:
                    log.exception(
                        "[GIVEAWAY] Gewinner-DM an %s "
                        "fehlgeschlagen.",
                        user_id,
                    )

        winner_text = (
            "\n".join(
                f"🏆 {mention}"
                for mention in winner_mentions
            )
            if winner_mentions
            else "😢 Keine gültigen Teilnehmer."
        )

        claim_note = (
            "🎫 Die Gewinner haben eine private Nachricht mit "
            "ihrem persönlichen Ticket-Button erhalten."
        )

        if auto_ticket_count:
            claim_note += (
                f"\n📩 Für {auto_ticket_count} Gewinner mit "
                "geschlossenen DMs wurde automatisch ein Ticket "
                "erstellt."
            )

        embed = discord.Embed(
            title=(
                f"🏁 Giveaway beendet – "
                f"{giveaway['title']}"
            ),
            description=(
                f"{DIVIDER}\n"
                f"🎁 **Gewinn:** {giveaway['prize']}\n\n"
                f"**Gewinner:**\n"
                f"{winner_text}\n"
                f"{DIVIDER}\n\n"
                f"{claim_note}\n\n"
                "Danke an alle Teilnehmer! ❤️"
            ),
            color=discord.Color.gold(),
        )

        embed.set_footer(
            text=f"Giveaway ID: {giveaway['id']} • Beendet"
        )

        for message_data in giveaway.get(
            "messages",
            [],
        ):
            try:
                channel = await resolve_channel(
                    self.bot,
                    message_data["channel_id"],
                )

                if channel is None:
                    continue

                message = await channel.fetch_message(
                    message_data["message_id"]
                )

                await message.edit(
                    content="🏁 **GIVEAWAY BEENDET**",
                    embed=embed,
                    view=None,
                )

            except Exception:
                log.exception(
                    "[GIVEAWAY] Ergebnis konnte nicht aktualisiert werden."
                )

        for channel_id in giveaway.get(
            "channels",
            [],
        ):
            try:
                channel = await resolve_channel(
                    self.bot,
                    channel_id,
                )

                if channel is None:
                    continue

                await channel.send(
                    embed=embed
                )

            except Exception:
                log.exception(
                    "[GIVEAWAY] Ergebnis konnte nicht gesendet werden."
                )

        self._giveaway_views.pop(
            giveaway["id"],
            None,
        )

        await self.save_giveaways()

        log.info(
            "[GIVEAWAY] Giveaway %s beendet. Gewinner: %s "
            "(DMs: %s, Auto-Tickets: %s)",
            giveaway["id"],
            winners,
            dm_sent_count,
            auto_ticket_count,
        )

    # ========================================================
    # GIVEAWAY SCHEDULER
    # ========================================================

    @tasks.loop(seconds=15)
    async def giveaway_scheduler(self):
        if not self.giveaways:
            return

        now = utc_now()

        for giveaway in list(
            self.giveaways.values()
        ):
            if giveaway.get("ended"):
                continue

            try:
                end_at = string_to_datetime(
                    giveaway["end_at"]
                )
            except Exception:
                continue

            if end_at <= now:
                await self.finish_giveaway(
                    giveaway
                )

    @giveaway_scheduler.before_loop
    async def before_giveaway_scheduler(self):
        await self.bot.wait_until_ready()

    # ========================================================
    # /announce-panel
    # ========================================================

    @app_commands.command(
        name="announce-panel",
        description=(
            "Erstellt oder aktualisiert das permanente "
            "Announcement Panel."
        ),
    )
    async def announce_panel(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Nur auf einem Server möglich.",
                ephemeral=True,
            )
            return

        if not has_announcement_permission(
            interaction
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, "
                "diesen Befehl zu nutzen.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        await self.ensure_panel()

        await interaction.followup.send(
            "✅ Das permanente Announcement Panel "
            "wurde aktualisiert.",
            ephemeral=True,
        )

    # ========================================================
    # /announce-guide
    # ========================================================

    @app_commands.command(
        name="announce-guide",
        description=(
            "Zeigt eine Anleitung, wie der Announcement-Bot funktioniert."
        ),
    )
    async def announce_guide(
        self,
        interaction: discord.Interaction,
    ):
        embed = discord.Embed(
            title="📖 Announcement-Bot – Leitfaden",
            description=(
                "Hier ist eine Übersicht über alles, "
                "was der Bot kann. Das permanente Panel "
                "findet ihr im Announcement-Kanal."
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="📂 1. Kategorie & 🎨 Template wählen",
            value=(
                "Oben im Panel wählt ihr zuerst eine Kategorie "
                "und danach ein passendes vorgefertigtes Template."
            ),
            inline=False,
        )

        embed.add_field(
            name="📢 2. Zielkanäle auswählen",
            value=(
                "Über das Kanal-Menü könnt ihr bis zu 25 "
                "Text- oder News-Kanäle als Ziel auswählen."
            ),
            inline=False,
        )

        embed.add_field(
            name="📝 Inhalt & 🔗 Buttons",
            value=(
                "**Inhalt:** Titel, Text, Ping, Bild-URL "
                "und Farbe frei anpassen.\n"
                "**Buttons:** Bis zu 5 Link-Buttons."
            ),
            inline=False,
        )

        embed.add_field(
            name="👀 Vorschau, 🚀 Senden, 🕐 Planen",
            value=(
                "**Vorschau:** Zeigt die Nachricht privat.\n"
                "**Senden:** Verschickt sie sofort.\n"
                "**Planen:** Legt Datum/Uhrzeit fest."
            ),
            inline=False,
        )

        embed.add_field(
            name="🎁 Giveaways",
            value=(
                "Erstellt automatische Giveaways mit Preis, "
                "Gewinneranzahl, Dauer und optionaler "
                "Gewinner-Rolle. Teilnehmerzahl und Countdown "
                "aktualisieren sich live. Gewinner erhalten "
                "nach Ende automatisch einen persönlichen "
                "🎫 Claim-Button per DM, um ihr Ticket zu öffnen."
            ),
            inline=False,
        )

        permission_text = (
            "Nur **Administratoren**"
            if REQUIRE_ADMINISTRATOR
            else (
                "Mitglieder mit `Server verwalten` "
                "oder Administrator"
            )
        )

        if ALLOWED_ROLE_IDS:
            permission_text += (
                " sowie freigeschaltete Rollen"
            )

        embed.add_field(
            name="🔒 Berechtigungen",
            value=permission_text,
            inline=False,
        )

        if (
            self.bot.user
            and self.bot.user.display_avatar
        ):
            embed.set_thumbnail(
                url=self.bot.user.display_avatar.url
            )

        embed.set_footer(
            text="Announcement-Bot • /announce-guide"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # ========================================================
    # /announce
    # ========================================================

    @app_commands.command(
        name="announce",
        description=(
            "Öffnet die private Announcement-Verwaltung."
        ),
    )
    async def announce(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Nur auf einem Server möglich.",
                ephemeral=True,
            )
            return

        if not has_announcement_permission(
            interaction
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, "
                "diesen Befehl zu nutzen.",
                ephemeral=True,
            )
            return

        panel = AnnouncementPanel(
            self
        )

        await interaction.response.send_message(
            embed=panel.make_panel_embed(),
            view=panel,
            ephemeral=True,
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Announcements(bot)
    )
