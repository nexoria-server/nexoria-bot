import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

# ============================================================
# KONFIGURATION
# ============================================================

APPLICATION_PANEL_CHANNEL_ID = 1529086680533831751
APPLICATION_CATEGORY_ID = 1535739435805581423
APPLICATION_LIST_CHANNEL_ID = 1535748337037479956
APPLICATION_SEARCH_CHANNEL_ID = 1535749442601230437

MEDIA_ROLE_ID = 1527099952730345574
TEST_SUPPORTER_ROLE_ID = 1527099612274364638
BUILDER_ROLE_ID = 1528052296099823808

# Neue Auto-Rollen
DEVELOPER_ROLE_ID = 1527099942446039040
PARTNER_ROLE_ID = 1528510196144672882

DATA_FILE = Path("applications.json")

# ============================================================
# BEWERBUNGSTYPEN
# ============================================================

APPLICATION_TYPES = {
    # ========================================================
    # TEST-SUPPORTER / HELFER
    # ========================================================

    "test_supporter": {
        "name": "Test-Supporter",
        "emoji": "🛡️",
        "role_id": TEST_SUPPORTER_ROLE_ID,
        "color": discord.Color.blurple(),

        "requirements": (
            "• Freundliches und respektvolles Auftreten\n"
            "• Gute Kenntnisse über Discord und NexoriaCraft\n"
            "• Spielern bei Fragen und Problemen helfen können\n"
            "• Ruhiges Verhalten auch bei Konflikten\n"
            "• Teamfähigkeit und Zuverlässigkeit\n"
            "• Regelmäßige Aktivität auf dem Server\n"
            "• Bereitschaft, sich in die Teamstrukturen einzuarbeiten"
        ),

        "questions": (
            "**Bitte kopiere diese Liste und beantworte alle Punkte:**\n\n"
            "1. **Minecraft-Name:**\n"
            "2. **Discord-Name:**\n"
            "3. **Alter:**\n"
            "4. **Wie lange spielst du bereits auf NexoriaCraft?**\n"
            "5. **Wie lange bist du bereits auf Discord aktiv?**\n"
            "6. **Hast du bereits Erfahrungen im Support? Wenn ja, wo?**\n"
            "7. **Warum möchtest du Test-Supporter bei NexoriaCraft werden?**\n"
            "8. **Was macht für dich einen guten Supporter aus?**\n"
            "9. **Ein Spieler beleidigt dich während eines Supportfalls. Wie reagierst du?**\n"
            "10. **Ein Spieler behauptet, ungerecht gebannt worden zu sein. Wie gehst du vor?**\n"
            "11. **Was würdest du tun, wenn du die Antwort auf eine Spielerfrage nicht kennst?**\n"
            "12. **Wie würdest du mit einem Streit zwischen zwei Spielern umgehen?**\n"
            "13. **Wie viele Stunden pro Woche bist du ungefähr aktiv?**\n"
            "14. **Zu welchen Zeiten bist du meistens online?**\n"
            "15. **Warum sollten wir gerade dich als Test-Supporter auswählen?**\n"
            "16. **Gibt es noch etwas, das wir über dich wissen sollten?**"
        ),
    },

    # ========================================================
    # BUILDER
    # ========================================================

    "builder": {
        "name": "Builder",
        "emoji": "🧱",
        "role_id": BUILDER_ROLE_ID,
        "color": discord.Color.orange(),

        "requirements": (
            "• Kreativität und gutes Auge für Details\n"
            "• Erfahrung im Minecraft-Building\n"
            "• Teamfähigkeit\n"
            "• Saubere und strukturierte Arbeitsweise\n"
            "• Eigene Ideen einbringen können\n"
            "• Vorgaben zuverlässig umsetzen können\n"
            "• WorldEdit-/VoxelSniper-Erfahrung ist von Vorteil\n"
            "• Bilder oder ein Portfolio eigener Builds sind erwünscht"
        ),

        "questions": (
            "**Bitte kopiere diese Liste und beantworte alle Punkte:**\n\n"
            "1. **Minecraft-Name:**\n"
            "2. **Discord-Name:**\n"
            "3. **Alter:**\n"
            "4. **Wie lange baust du bereits in Minecraft?**\n"
            "5. **Welche Baustile beherrschst du?**\n"
            "6. **Wie würdest du deinen persönlichen Baustil beschreiben?**\n"
            "7. **Welche größeren Builds/Projekte hast du bereits umgesetzt?**\n"
            "8. **Auf welchen Servern oder Projekten hast du bereits gebaut?**\n"
            "9. **Welche Tools und Plugins kennst du? (z. B. WorldEdit, VoxelSniper)**\n"
            "10. **Wie gut kannst du nach einer Vorlage oder festen Vorgabe bauen?**\n"
            "11. **Wie gehst du mit Kritik an deinen Builds um?**\n"
            "12. **Wie würdest du dich mit anderen Buildern abstimmen?**\n"
            "13. **Hast du ein Portfolio oder Bilder deiner Builds? Bitte Links einfügen.**\n"
            "14. **Wie viele Stunden pro Woche kannst du ungefähr für das Projekt aufbringen?**\n"
            "15. **Warum möchtest du Builder bei NexoriaCraft werden?**\n"
            "16. **Welche Art von Bauprojekt würdest du gerne für NexoriaCraft umsetzen?**\n"
            "17. **Gibt es noch etwas, das wir wissen sollten?**"
        ),
    },

    # ========================================================
    # MEDIA
    # ========================================================

    "media": {
        "name": "Media",
        "emoji": "🎥",
        "role_id": MEDIA_ROLE_ID,
        "color": discord.Color.red(),

        "requirements": (
            "• Aktiver Content Creator\n"
            "• Öffentlicher YouTube-/TikTok-/Social-Media-Account\n"
            "• Regelmäßiger Content\n"
            "• Seriöses und respektvolles Auftreten\n"
            "• Content mit Bezug zu Minecraft/NexoriaCraft\n"
            "• Nachvollziehbare Reichweite\n"
            "• Bereitschaft, NexoriaCraft angemessen zu präsentieren"
        ),

        "questions": (
            "**Bitte kopiere diese Liste und beantworte alle Punkte:**\n\n"
            "1. **Minecraft-Name:**\n"
            "2. **Discord-Name:**\n"
            "3. **Alter:**\n"
            "4. **Welche Plattform(en) nutzt du? (YouTube, TikTok, Twitch, Instagram etc.)**\n"
            "5. **Link(s) zu deinen Social-Media-Kanälen:**\n"
            "6. **Wie viele Abonnenten/Follower hast du aktuell?**\n"
            "7. **Wie viele durchschnittliche Aufrufe erhält dein Content?**\n"
            "8. **Wie oft veröffentlichst du ungefähr neuen Content?**\n"
            "9. **Welche Art von Minecraft-Content erstellst du?**\n"
            "10. **Hast du bereits Content über andere Minecraft-Server erstellt? Wenn ja, welche?**\n"
            "11. **Welche Art von Content möchtest du speziell über NexoriaCraft erstellen?**\n"
            "12. **Warum möchtest du NexoriaCraft als Creator unterstützen?**\n"
            "13. **Wie würdest du NexoriaCraft in deinen Videos/Streams präsentieren?**\n"
            "14. **Hast du bereits Erfahrungen mit Kooperationen? Wenn ja, mit welchen Projekten?**\n"
            "15. **Wie oft könntest du ungefähr Content über NexoriaCraft veröffentlichen?**\n"
            "16. **Warum sollten wir dich als Media-Partner auswählen?**\n"
            "17. **Gibt es noch etwas, das wir wissen sollten?**"
        ),
    },

    # ========================================================
    # PARTNER
    # ========================================================

    "partner": {
        "name": "Partner",
        "emoji": "🤝",
        "role_id": PARTNER_ROLE_ID,
        "color": discord.Color.green(),

        "requirements": (
            "• Aktives und seriöses Projekt\n"
            "• Seriöse und respektvolle Kommunikation\n"
            "• Sinnvoller Bezug zu unserer Community\n"
            "• Gegenseitiger Nutzen für beide Projekte\n"
            "• Aktive Community\n"
            "• Langfristiges Interesse an einer Zusammenarbeit"
        ),

        "questions": (
            "**Bitte kopiere diese Liste und beantworte alle Punkte:**\n\n"
            "1. **Name des Projekts:**\n"
            "2. **Dein Name und deine Position im Projekt:**\n"
            "3. **Discord-/Projekt-Link:**\n"
            "4. **Was ist euer Projekt und was bietet ihr an?**\n"
            "5. **Wie lange existiert euer Projekt bereits?**\n"
            "6. **Wie viele Mitglieder hat eure Community aktuell?**\n"
            "7. **Wie aktiv ist eure Community ungefähr?**\n"
            "8. **Welche Plattformen nutzt ihr?**\n"
            "9. **Warum möchtet ihr eine Partnerschaft mit NexoriaCraft?**\n"
            "10. **Was könnt ihr NexoriaCraft konkret anbieten?**\n"
            "11. **Welche Vorteile hätte eine Partnerschaft für unsere Community?**\n"
            "12. **Was erwartet ihr im Gegenzug von NexoriaCraft?**\n"
            "13. **Wie stellt ihr euch die Partnerschaft konkret vor?**\n"
            "14. **Welche Art von Werbung oder gegenseitiger Unterstützung wäre geplant?**\n"
            "15. **Habt ihr bereits Partnerschaften mit anderen Projekten?**\n"
            "16. **Warum sollten wir gerade mit eurem Projekt zusammenarbeiten?**\n"
            "17. **Gibt es noch weitere wichtige Informationen?**"
        ),
    },

    # ========================================================
    # DEVELOPER
    # ========================================================

    "developer": {
        "name": "Developer",
        "emoji": "💻",
        "role_id": DEVELOPER_ROLE_ID,
        "color": discord.Color.dark_blue(),

        "requirements": (
            "• Gute Programmierkenntnisse\n"
            "• Sauberer und strukturierter Code\n"
            "• Teamfähigkeit\n"
            "• Zuverlässigkeit\n"
            "• Eigenständiges Arbeiten\n"
            "• Erfahrung mit Minecraft-/Discord-Entwicklung von Vorteil\n"
            "• Git-/GitHub-Erfahrung von Vorteil\n"
            "• Bereitschaft, sich in bestehende Systeme einzuarbeiten"
        ),

        "questions": (
            "**Bitte kopiere diese Liste und beantworte alle Punkte:**\n\n"
            "1. **Minecraft-Name:**\n"
            "2. **Discord-Name:**\n"
            "3. **Alter:**\n"
            "4. **Welche Programmiersprachen beherrschst du?**\n"
            "5. **Wie lange programmierst du bereits?**\n"
            "6. **Welche Programmiersprache verwendest du am liebsten und warum?**\n"
            "7. **Welche Minecraft-Plugins/Mods/Projekte hast du bereits entwickelt?**\n"
            "8. **Welche Erfahrungen hast du mit Spigot/Paper/Bukkit oder ähnlichen APIs?**\n"
            "9. **Welche Erfahrungen hast du mit Discord-Bots?**\n"
            "10. **Welche Erfahrungen hast du mit Python/discord.py?**\n"
            "11. **Kennst du Git und GitHub? Wenn ja, wie gut?**\n"
            "12. **Hast du bereits mit Datenbanken gearbeitet? Wenn ja, mit welchen?**\n"
            "13. **Wie gehst du vor, wenn du einen Fehler in einem bestehenden System findest?**\n"
            "14. **Wie gehst du mit Code-Reviews und Kritik an deinem Code um?**\n"
            "15. **Wie würdest du ein größeres Feature planen, bevor du mit der Programmierung beginnst?**\n"
            "16. **Hast du Referenzen, GitHub-Projekte oder Code-Beispiele? Bitte Links einfügen.**\n"
            "17. **Wie viele Stunden pro Woche kannst du ungefähr für NexoriaCraft aufbringen?**\n"
            "18. **Warum möchtest du Developer bei NexoriaCraft werden?**\n"
            "19. **Welche Bereiche würdest du bei NexoriaCraft gerne entwickeln?**\n"
            "20. **Gibt es noch etwas, das wir wissen sollten?**"
        ),
    },
}

# ============================================================
# DATEN
# ============================================================

def load_data():
    if not DATA_FILE.exists():
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        logging.exception("applications.json konnte nicht gelesen werden.")
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def now():
    return datetime.now(timezone.utc)


def format_date(value):
    if not value:
        return "Unbekannt"

    try:
        dt = datetime.fromisoformat(value)
        return f"<t:{int(dt.timestamp())}:F>"
    except Exception:
        return "Unbekannt"


def get_type_data(application_type):
    return APPLICATION_TYPES.get(application_type)


def find_open_application(guild, user_id):
    for channel in guild.text_channels:
        topic = channel.topic or ""

        if (
            topic.startswith("application:")
            and f"user_id={user_id}" in topic
        ):
            return channel

    return None


# ============================================================
# ENTSCHEIDUNGS-MODAL
# ============================================================

class DecisionModal(discord.ui.Modal):
    def __init__(
        self,
        application_type,
        accepted,
        applicant_id,
    ):
        self.application_type = application_type
        self.accepted = accepted
        self.applicant_id = applicant_id

        super().__init__(
            title=(
                "Bewerbung annehmen"
                if accepted
                else "Bewerbung ablehnen"
            )
        )

        self.note = discord.ui.TextInput(
            label="Optionale Nachricht",
            placeholder="Kann leer bleiben...",
            required=False,
            max_length=1000,
            style=discord.TextStyle.paragraph,
        )

        self.add_item(self.note)

    async def on_submit(self, interaction):
        cog = interaction.client.get_cog("Applications")

        if cog is None:
            await interaction.response.send_message(
                "❌ Bewerbungs-System nicht verfügbar.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        await cog.process_decision(
            interaction=interaction,
            application_type=self.application_type,
            applicant_id=self.applicant_id,
            accepted=self.accepted,
            note=self.note.value.strip(),
        )


# ============================================================
# ANNEHMEN / ABLEHNEN
# ============================================================

class DecisionView(discord.ui.View):
    def __init__(
        self,
        application_type,
        applicant_id,
    ):
        super().__init__(timeout=None)

        self.application_type = application_type
        self.applicant_id = applicant_id

    def is_admin(self, interaction):
        return interaction.user.guild_permissions.administrator

    @discord.ui.button(
        label="Annehmen",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="application_accept",
    )
    async def accept(self, interaction, button):
        if not self.is_admin(interaction):
            await interaction.response.send_message(
                "❌ Nur Administratoren dürfen Bewerbungen annehmen.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            DecisionModal(
                self.application_type,
                True,
                self.applicant_id,
            )
        )

    @discord.ui.button(
        label="Ablehnen",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="application_deny",
    )
    async def deny(self, interaction, button):
        if not self.is_admin(interaction):
            await interaction.response.send_message(
                "❌ Nur Administratoren dürfen Bewerbungen ablehnen.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            DecisionModal(
                self.application_type,
                False,
                self.applicant_id,
            )
        )


# ============================================================
# BEWERBUNGS-PANEL
# ============================================================

class ApplicationPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_application(self, interaction, application_type):
        cog = interaction.client.get_cog("Applications")

        if cog is None:
            await interaction.response.send_message(
                "❌ Bewerbungs-System nicht verfügbar.",
                ephemeral=True,
            )
            return

        await cog.create_application(
            interaction,
            application_type,
        )

    @discord.ui.button(
        label="Test-Supporter",
        emoji="🛡️",
        style=discord.ButtonStyle.primary,
        custom_id="application_test_supporter",
    )
    async def test_supporter(self, interaction, button):
        await self.create_application(
            interaction,
            "test_supporter",
        )

    @discord.ui.button(
        label="Builder",
        emoji="🧱",
        style=discord.ButtonStyle.secondary,
        custom_id="application_builder",
    )
    async def builder(self, interaction, button):
        await self.create_application(
            interaction,
            "builder",
        )

    @discord.ui.button(
        label="Media",
        emoji="🎥",
        style=discord.ButtonStyle.danger,
        custom_id="application_media",
    )
    async def media(self, interaction, button):
        await self.create_application(
            interaction,
            "media",
        )

    @discord.ui.button(
        label="Partner",
        emoji="🤝",
        style=discord.ButtonStyle.success,
        custom_id="application_partner",
    )
    async def partner(self, interaction, button):
        await self.create_application(
            interaction,
            "partner",
        )

    @discord.ui.button(
        label="Developer",
        emoji="💻",
        style=discord.ButtonStyle.secondary,
        custom_id="application_developer",
    )
    async def developer(self, interaction, button):
        await self.create_application(
            interaction,
            "developer",
        )


# ============================================================
# SUCH-MODAL
# ============================================================

class SearchModal(discord.ui.Modal):
    def __init__(self, application_type=None):
        self.application_type = application_type

        title = "Bewerber suchen"

        if application_type:
            config = get_type_data(application_type)

            if config:
                title = f"Suche: {config['name']}"

        super().__init__(title=title)

        self.search = discord.ui.TextInput(
            label="Spielername oder Discord-ID",
            placeholder="z. B. Luca oder 123456789",
            required=False,
            max_length=100,
        )

        self.add_item(self.search)

    async def on_submit(self, interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren dürfen die Suche benutzen.",
                ephemeral=True,
            )
            return

        cog = interaction.client.get_cog("Applications")

        if cog is None:
            await interaction.response.send_message(
                "❌ System nicht verfügbar.",
                ephemeral=True,
            )
            return

        await cog.search_applicant(
            interaction,
            self.search.value.strip(),
            self.application_type,
        )


# ============================================================
# SUCH-PANEL
# ============================================================

class SearchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_application_type = None

    @discord.ui.select(
        placeholder="Bewerbungsart auswählen...",
        custom_id="application_search_type",
        options=[
            discord.SelectOption(
                label="Alle Bewerbungen",
                value="all",
                emoji="📋",
            ),
            discord.SelectOption(
                label="Test-Supporter",
                value="test_supporter",
                emoji="🛡️",
            ),
            discord.SelectOption(
                label="Builder",
                value="builder",
                emoji="🧱",
            ),
            discord.SelectOption(
                label="Media",
                value="media",
                emoji="🎥",
            ),
            discord.SelectOption(
                label="Partner",
                value="partner",
                emoji="🤝",
            ),
            discord.SelectOption(
                label="Developer",
                value="developer",
                emoji="💻",
            ),
        ],
    )
    async def application_type_select(
        self,
        interaction,
        select,
    ):
        selected = select.values[0]

        if selected == "all":
            self.selected_application_type = None
            display_name = "Alle Bewerbungen"
        else:
            self.selected_application_type = selected
            config = get_type_data(selected)
            display_name = config["name"] if config else selected

        await interaction.response.send_message(
            f"✅ Filter gesetzt: **{display_name}**\n"
            "Klicke jetzt auf **Bewerber suchen**.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Bewerber suchen",
        emoji="🔎",
        style=discord.ButtonStyle.primary,
        custom_id="application_search",
    )
    async def search(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren dürfen die Bewerber-Suche benutzen.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            SearchModal(self.selected_application_type)
        )


# ============================================================
# COG
# ============================================================

class Applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    # ========================================================
    # PANEL POSTEN
    # ========================================================

    @app_commands.command(
        name="bewerbung_panel",
        description="Postet das Bewerbungs-Panel.",
    )
    @app_commands.default_permissions(administrator=True)
    async def bewerbung_panel(self, interaction):
        channel = interaction.guild.get_channel(
            APPLICATION_PANEL_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Bewerbungs-Panel-Kanal wurde nicht gefunden.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📋 NexoriaCraft – Team-Bewerbungen",
            description=(
                "## 👋 Du möchtest Teil von NexoriaCraft werden?\n\n"
                "Bei **NexoriaCraft** suchen wir engagierte, "
                "zuverlässige und motivierte Leute für verschiedene "
                "Bereiche.\n\n"
                "Wähle unten die Bewerbung aus, die zu dir passt.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

                "🛡️ **Test-Supporter**\n"
                "Hilf Spielern, beantworte Fragen und unterstütze "
                "unser Support-Team.\n\n"

                "🧱 **Builder**\n"
                "Gestalte unsere Minecraft-Welt und bringe deine "
                "eigenen Bauideen ein.\n\n"

                "🎥 **Media**\n"
                "Erstelle Content über NexoriaCraft und hilf dabei, "
                "unseren Server bekannter zu machen.\n\n"

                "🤝 **Partner**\n"
                "Du möchtest dein Projekt oder deine Community mit "
                "NexoriaCraft verbinden? Dann ist diese Bewerbung "
                "für dich.\n\n"

                "💻 **Developer**\n"
                "Entwickle Bots, Plugins und Systeme und unterstütze "
                "uns bei der technischen Weiterentwicklung von "
                "NexoriaCraft.\n\n"

                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

                "### 📌 Wichtig\n"
                "Nach dem Öffnen eines Tickets bekommst du eine "
                "ausführliche Liste mit den Informationen, die wir "
                "für deine Bewerbung benötigen.\n\n"

                "Bitte beantworte die Punkte ehrlich und möglichst "
                "vollständig.\n\n"

                "♾️ **Bewerbungen können jederzeit erneut erstellt "
                "werden.**\n\n"

                "⚠️ Eine Bewerbung garantiert **keine Aufnahme**."
            ),
            color=discord.Color.blurple(),
        )

        embed.set_footer(text="NexoriaCraft • Team-Bewerbungen")

        await channel.send(
            embed=embed,
            view=ApplicationPanel(),
        )

        await interaction.response.send_message(
            f"✅ Bewerbungs-Panel wurde in {channel.mention} gepostet.",
            ephemeral=True,
        )

    # ========================================================
    # SUCH-PANEL POSTEN
    # ========================================================

    @app_commands.command(
        name="bewerbung_suche",
        description="Postet das Admin-Suchsystem.",
    )
    @app_commands.default_permissions(administrator=True)
    async def bewerbung_suche(self, interaction):
        channel = interaction.guild.get_channel(
            APPLICATION_SEARCH_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Suchkanal wurde nicht gefunden.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🔎 Bewerberverwaltung",
            description=(
                "## 👥 Bewerber suchen\n\n"
                "Hier können Administratoren Bewerber suchen "
                "und deren Bewerbungsinformationen einsehen.\n\n"

                "### 🔍 So funktioniert die Suche\n"
                "1. Wähle oben die **Bewerbungsart** aus.\n"
                "2. Klicke auf **Bewerber suchen**.\n"
                "3. Gib den Spieler-Namen oder die Discord-ID ein.\n\n"

                "### 📊 Angezeigt werden\n"
                "• 👤 Discord-Name\n"
                "• 🆔 Discord-ID\n"
                "• 📋 Bewerbungsart\n"
                "• 📌 Status\n"
                "• 📅 Letzte Bewerbung\n"
                "• 📊 Anzahl der Bewerbungen\n"
                "• ♾️ Nächste Bewerbung: jederzeit möglich\n\n"

                "Nur Administratoren können die Ergebnisse sehen."
            ),
            color=discord.Color.blurple(),
        )

        embed.set_footer(text="NexoriaCraft • Bewerberverwaltung")

        await channel.send(
            embed=embed,
            view=SearchView(),
        )

        await interaction.response.send_message(
            f"✅ Suchsystem wurde in {channel.mention} gepostet.",
            ephemeral=True,
        )

    # ========================================================
    # BEWERBUNG ERSTELLEN
    # ========================================================

    async def create_application(
        self,
        interaction,
        application_type,
    ):
        config = get_type_data(application_type)

        if config is None:
            await interaction.response.send_message(
                "❌ Ungültige Bewerbungsart.",
                ephemeral=True,
            )
            return

        existing = find_open_application(
            interaction.guild,
            interaction.user.id,
        )

        if existing:
            await interaction.response.send_message(
                f"❌ Du hast bereits ein offenes "
                f"Bewerbungs-Ticket: {existing.mention}\n\n"
                "Schließe dein aktuelles Ticket zuerst, "
                "bevor du ein neues erstellst.",
                ephemeral=True,
            )
            return

        category = interaction.guild.get_channel(
            APPLICATION_CATEGORY_ID
        )

        if category is None:
            await interaction.response.send_message(
                "❌ Die Bewerbungs-Kategorie wurde nicht gefunden.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        overwrites = {
            interaction.guild.default_role:
                discord.PermissionOverwrite(view_channel=False),

            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                ),

            interaction.guild.me:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True,
                ),
        }

        for member in interaction.guild.members:
            if member.guild_permissions.administrator:
                overwrites[member] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )

        safe_name = interaction.user.name.lower()
        safe_name = "".join(
            char if char.isalnum() else "-"
            for char in safe_name
        )

        channel_name = (
            f"bewerbung-{application_type}-{safe_name}"
        )[:95]

        channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=(
                f"application:{application_type};"
                f"user_id={interaction.user.id}"
            ),
            reason="Neue Team-Bewerbung",
        )

        user_key = str(interaction.user.id)

        old_count = self.data.get(
            user_key,
            {},
        ).get(
            "applications_count",
            0,
        )

        self.data[user_key] = {
            "username": str(interaction.user),
            "user_id": interaction.user.id,
            "last_application": now().isoformat(),
            "last_type": application_type,
            "status": "offen",
            "applications_count": old_count + 1,
        }

        save_data(self.data)

        embed = discord.Embed(
            title=(
                f"{config['emoji']} "
                f"{config['name']}-Bewerbung"
            ),
            description=(
                f"Willkommen {interaction.user.mention}!\n\n"
                f"Du hast eine **{config['name']}-Bewerbung** "
                "eröffnet.\n\n"
                "Bitte lies dir alles sorgfältig durch und "
                "beantworte anschließend die Bewerbung.\n\n"

                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

                "## 📌 Voraussetzungen\n\n"
                f"{config['requirements']}\n\n"

                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

                "## 📝 Deine Bewerbung\n\n"
                f"{config['questions']}\n\n"

                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

                "## ⚠️ Wichtig\n\n"
                "Bitte kopiere die komplette Liste und beantworte "
                "jeden Punkt.\n\n"

                "Du kannst deine Antworten in **einer oder mehreren "
                "Nachrichten** senden.\n\n"

                "Ein Administrator wird deine Bewerbung anschließend "
                "prüfen."
            ),
            color=config["color"],
        )

        embed.set_footer(
            text=f"NexoriaCraft • {config['name']}-Bewerbung"
        )

        await channel.send(
            content=(
                f"👋 Hallo {interaction.user.mention}!\n\n"
                f"Dein **{config['name']}-Bewerbungs-Ticket** "
                "wurde erfolgreich erstellt."
            ),
            embed=embed,
        )

        decision_embed = discord.Embed(
            title="⚖️ Bewerbung bearbeiten",
            description=(
                "Wenn die Bewerbung vollständig ist, kann ein "
                "Administrator die Bewerbung bearbeiten.\n\n"

                "✅ **Annehmen**\n"
                f"Der Bewerber bekommt automatisch die "
                f"**{config['name']}-Rolle**, sofern eine Rolle "
                "konfiguriert ist.\n\n"

                "❌ **Ablehnen**\n"
                "Der Bewerber erhält eine DM. Dabei kann optional "
                "eine persönliche Nachricht hinzugefügt werden.\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                "♾️ **Der Bewerber kann sich nach der Entscheidung "
                "jederzeit erneut bewerben.**"
            ),
            color=discord.Color.dark_grey(),
        )

        await channel.send(
            embed=decision_embed,
            view=DecisionView(
                application_type,
                interaction.user.id,
            ),
        )

        await interaction.followup.send(
            f"✅ Deine **{config['name']}-Bewerbung** wurde erstellt:\n"
            f"{channel.mention}",
            ephemeral=True,
        )

        await self.update_application_list(interaction.guild)

    # ========================================================
    # ENTSCHEIDUNG
    # ========================================================

    async def process_decision(
        self,
        interaction,
        application_type,
        applicant_id,
        accepted,
        note,
    ):
        config = get_type_data(application_type)

        if config is None:
            return

        member = interaction.guild.get_member(applicant_id)

        if member is None:
            try:
                member = await interaction.guild.fetch_member(applicant_id)
            except Exception:
                member = None

        user_key = str(applicant_id)

        applicant_data = self.data.setdefault(
            user_key,
            {
                "username": str(member) if member else str(applicant_id),
                "user_id": applicant_id,
                "applications_count": 1,
            },
        )

        applicant_data["status"] = (
            "angenommen"
            if accepted
            else "abgelehnt"
        )

        applicant_data["last_decision"] = now().isoformat()
        applicant_data["last_type"] = application_type

        save_data(self.data)

        # ====================================================
        # AUTO-ROLLE BEI ANNAHME
        # ====================================================

        if accepted and member:
            role_id = config["role_id"]

            if role_id:
                role = interaction.guild.get_role(role_id)

                if role:
                    try:
                        await member.add_roles(
                            role,
                            reason=(
                                f"{config['name']}-Bewerbung "
                                "angenommen"
                            ),
                        )
                    except Exception:
                        logging.exception(
                            "Rolle konnte nicht vergeben werden."
                        )
                else:
                    logging.warning(
                        "Rolle %s für %s wurde nicht gefunden.",
                        role_id,
                        config["name"],
                    )

        # ====================================================
        # DM
        # ====================================================

        if member:
            try:
                if accepted:
                    accepted_messages = {
                        "test_supporter": (
                            f"Hallo {member.mention}!\n\n"
                            "wir freuen uns, dir mitteilen zu können, "
                            "dass deine **Test-Supporter-Bewerbung** bei "
                            "**NexoriaCraft** angenommen wurde! 🎉\n\n"
                            "Du hast uns mit deiner Bewerbung überzeugt "
                            "und erhältst nun die Möglichkeit, dich als "
                            "Teil unseres Support-Teams zu beweisen.\n\n"
                            "🛡️ **Deine nächsten Schritte:**\n"
                            "• Lies dir die Teamregeln sorgfältig durch.\n"
                            "• Mach dich mit unseren Support-Abläufen vertraut.\n"
                            "• Bei Fragen kannst du dich an die Teamleitung wenden.\n"
                            "• Arbeite freundlich und respektvoll mit unseren Spielern.\n\n"
                            "Wir freuen uns auf die Zusammenarbeit mit dir! ❤️"
                        ),

                        "builder": (
                            f"Hallo {member.mention}!\n\n"
                            "deine **Builder-Bewerbung** bei **NexoriaCraft** "
                            "wurde angenommen! 🎉\n\n"
                            "Wir freuen uns sehr, dich künftig bei der "
                            "Gestaltung unseres Projekts dabei zu haben. 🧱\n\n"
                            "🏗️ **Deine nächsten Schritte:**\n"
                            "• Besprich dich mit dem Build-Team.\n"
                            "• Halte dich an unsere Bauvorgaben.\n"
                            "• Arbeite sauber und strukturiert.\n"
                            "• Bringe gerne eigene Ideen und Vorschläge ein.\n\n"
                            "Wir freuen uns auf deine Builds und die "
                            "gemeinsame Arbeit an NexoriaCraft! ❤️"
                        ),

                        "media": (
                            f"Hallo {member.mention}!\n\n"
                            "deine **Media-Bewerbung** bei **NexoriaCraft** "
                            "wurde angenommen! 🎥🎉\n\n"
                            "Wir freuen uns darauf, gemeinsam mit dir "
                            "Content rund um NexoriaCraft zu erstellen.\n\n"
                            "🎥 **Deine nächsten Schritte:**\n"
                            "• Besprich Content-Ideen mit dem Media-Team.\n"
                            "• Stelle NexoriaCraft seriös und positiv dar.\n"
                            "• Halte dich an unsere Media-Vorgaben.\n"
                            "• Informiere das Team nach Möglichkeit über geplanten Content.\n\n"
                            "Wir freuen uns auf die Zusammenarbeit und "
                            "deinen Content! ❤️"
                        ),

                        "partner": (
                            f"Hallo {member.mention}!\n\n"
                            "wir freuen uns, dir mitteilen zu können, "
                            "dass eure **Partnerschaftsanfrage** bei "
                            "**NexoriaCraft** angenommen wurde! 🤝🎉\n\n"
                            "Wir freuen uns auf eine erfolgreiche und "
                            "langfristige Zusammenarbeit mit eurem Projekt.\n\n"
                            "🤝 **Wie geht es weiter?**\n"
                            "• Die weiteren Schritte werden mit der Teamleitung besprochen.\n"
                            "• Absprachen zur gegenseitigen Werbung werden gemeinsam getroffen.\n"
                            "• Beide Projekte sollten die vereinbarten Bedingungen einhalten.\n"
                            "• Bei Änderungen oder Fragen könnt ihr euch jederzeit melden.\n\n"
                            "Vielen Dank für euer Vertrauen und auf eine "
                            "erfolgreiche Partnerschaft! ❤️"
                        ),

                        "developer": (
                            f"Hallo {member.mention}!\n\n"
                            "deine **Developer-Bewerbung** bei **NexoriaCraft** "
                            "wurde angenommen! 💻🎉\n\n"
                            "Wir freuen uns, dich künftig bei der technischen "
                            "Weiterentwicklung unseres Projekts dabei zu haben.\n\n"
                            "💻 **Deine nächsten Schritte:**\n"
                            "• Besprich dich mit dem Development-Team.\n"
                            "• Mach dich mit unserem bestehenden Code vertraut.\n"
                            "• Halte dich an unsere Entwicklungsstandards.\n"
                            "• Teste Änderungen sorgfältig, bevor sie live gehen.\n"
                            "• Sprich größere Änderungen vorher mit der Teamleitung ab.\n\n"
                            "Wir freuen uns auf deine Ideen und deine "
                            "Unterstützung bei der Entwicklung von NexoriaCraft! ❤️"
                        ),
                    }

                    message = accepted_messages.get(
                        application_type,
                        (
                            f"Hallo {member.mention}!\n\n"
                            "deine Bewerbung bei NexoriaCraft wurde angenommen! 🎉"
                        ),
                    )

                    dm_embed = discord.Embed(
                        title=(
                            f"{config['emoji']} "
                            f"{config['name']}-Bewerbung angenommen!"
                        ),
                        description=message,
                        color=discord.Color.green(),
                    )

                else:
                    rejected_messages = {
                        "test_supporter": (
                            f"Hallo {member.mention}!\n\n"
                            "vielen Dank für deine Bewerbung als "
                            "**Test-Supporter** bei **NexoriaCraft**.\n\n"
                            "Nach sorgfältiger Prüfung haben wir uns "
                            "dieses Mal leider dazu entschieden, deine "
                            "Bewerbung nicht anzunehmen.\n\n"
                            "Bitte verstehe diese Entscheidung nicht als "
                            "endgültige Ablehnung deiner Person. ❤️\n\n"
                            "Du kannst dich **jederzeit erneut bewerben** "
                            "und deine Bewerbung mit neuen Erfahrungen "
                            "oder Informationen verbessern.\n\n"
                            "Wir wünschen dir weiterhin viel Erfolg "
                            "auf NexoriaCraft!"
                        ),

                        "builder": (
                            f"Hallo {member.mention}!\n\n"
                            "vielen Dank für deine **Builder-Bewerbung** "
                            "bei **NexoriaCraft**.\n\n"
                            "Nach sorgfältiger Prüfung haben wir uns "
                            "dieses Mal leider gegen eine Aufnahme in "
                            "unser Builder-Team entschieden.\n\n"
                            "Das bedeutet nicht, dass wir deine "
                            "Baukenntnisse grundsätzlich schlecht finden.\n\n"
                            "Du kannst dich **jederzeit erneut bewerben** "
                            "und uns beispielsweise neue Builds oder "
                            "weitere Erfahrungen zeigen. 🧱\n\n"
                            "Wir wünschen dir weiterhin viel Erfolg "
                            "und vielleicht klappt es beim nächsten Mal! ❤️"
                        ),

                        "media": (
                            f"Hallo {member.mention}!\n\n"
                            "vielen Dank für dein Interesse an einer "
                            "**Media-Zusammenarbeit mit NexoriaCraft**.\n\n"
                            "Nach sorgfältiger Prüfung haben wir uns "
                            "dieses Mal leider dazu entschieden, deine "
                            "Media-Bewerbung nicht anzunehmen.\n\n"
                            "Bitte sieh diese Entscheidung nicht als "
                            "endgültiges Nein. ❤️\n\n"
                            "Du kannst dich **jederzeit erneut bewerben**, "
                            "beispielsweise wenn sich deine Reichweite, "
                            "dein Content oder deine bisherigen Erfahrungen "
                            "weiterentwickelt haben.\n\n"
                            "Vielen Dank für deine Zeit und dein Interesse "
                            "an NexoriaCraft!"
                        ),

                        "partner": (
                            f"Hallo {member.mention}!\n\n"
                            "vielen Dank für eure **Partnerschaftsanfrage "
                            "an NexoriaCraft**. 🤝\n\n"
                            "Nach sorgfältiger Prüfung haben wir uns "
                            "dieses Mal leider dazu entschieden, die "
                            "Partnerschaft nicht einzugehen.\n\n"
                            "Dies bedeutet nicht, dass eine zukünftige "
                            "Zusammenarbeit ausgeschlossen ist.\n\n"
                            "Ihr könnt euch **jederzeit erneut an uns "
                            "wenden**, wenn sich euer Projekt oder die "
                            "Rahmenbedingungen verändert haben.\n\n"
                            "Vielen Dank für euer Interesse und viel Erfolg "
                            "mit eurem Projekt!"
                        ),

                        "developer": (
                            f"Hallo {member.mention}!\n\n"
                            "vielen Dank für deine **Developer-Bewerbung** "
                            "bei **NexoriaCraft**.\n\n"
                            "Nach sorgfältiger Prüfung haben wir uns "
                            "dieses Mal leider gegen eine Aufnahme in "
                            "unser Development-Team entschieden.\n\n"
                            "Bitte verstehe dies nicht als endgültiges "
                            "Nein zu einer zukünftigen Zusammenarbeit. ❤️\n\n"
                            "Du kannst dich **jederzeit erneut bewerben** "
                            "und uns beispielsweise neue Projekte, "
                            "GitHub-Repositories oder weitere Erfahrungen "
                            "zeigen.\n\n"
                            "Wir wünschen dir weiterhin viel Erfolg beim "
                            "Programmieren und vielleicht klappt es "
                            "beim nächsten Mal!"
                        ),
                    }

                    message = rejected_messages.get(
                        application_type,
                        (
                            f"Hallo {member.mention}!\n\n"
                            "vielen Dank für deine Bewerbung bei NexoriaCraft. "
                            "Leider wurde sie dieses Mal abgelehnt."
                        ),
                    )

                    dm_embed = discord.Embed(
                        title=(
                            f"{config['emoji']} "
                            f"{config['name']}-Bewerbung abgelehnt"
                        ),
                        description=message,
                        color=discord.Color.red(),
                    )

                if note:
                    dm_embed.add_field(
                        name="💬 Persönliche Nachricht der Teamleitung",
                        value=note,
                        inline=False,
                    )

                dm_embed.set_footer(
                    text="NexoriaCraft • Bewerbungs-Team"
                )

                await member.send(embed=dm_embed)

            except discord.Forbidden:
                logging.warning(
                    "DM an %s konnte nicht gesendet werden.",
                    applicant_id,
                )
            except Exception:
                logging.exception(
                    "Fehler beim Senden der Bewerbungs-DM an %s.",
                    applicant_id,
                )

        # ====================================================
        # TICKET NACH ENTSCHEIDUNG
        # ====================================================

        channel = interaction.channel

        decision_embed = discord.Embed(
            title=(
                "✅ Bewerbung angenommen"
                if accepted
                else "❌ Bewerbung abgelehnt"
            ),
            description=(
                f"Die **{config['name']}-Bewerbung** wurde von "
                f"{interaction.user.mention} "
                f"{'angenommen' if accepted else 'abgelehnt'}."
            ),
            color=(
                discord.Color.green()
                if accepted
                else discord.Color.red()
            ),
        )

        if note:
            decision_embed.add_field(
                name="💬 Team-Notiz",
                value=note,
                inline=False,
            )

        decision_embed.add_field(
            name="♾️ Erneute Bewerbung",
            value=(
                "Der Bewerber kann jederzeit ein neues Ticket erstellen."
            ),
            inline=False,
        )

        try:
            await channel.send(embed=decision_embed)
        except Exception:
            logging.exception(
                "Entscheidung konnte nicht gepostet werden."
            )

        await self.update_application_list(interaction.guild)

        await interaction.followup.send(
            "✅ Entscheidung wurde gespeichert.",
            ephemeral=True,
        )

        delete_after = 3600 if accepted else 600

        await asyncio.sleep(delete_after)

        try:
            await channel.delete(
                reason="Bewerbungs-Ticket automatisch geschlossen"
            )
        except discord.NotFound:
            pass
        except Exception:
            logging.exception(
                "Bewerbungs-Ticket konnte nicht gelöscht werden."
            )

    # ========================================================
    # BEWERBER SUCHEN
    # ========================================================

    async def search_applicant(
        self,
        interaction,
        query,
        application_type=None,
    ):
        query_lower = query.lower()
        results = []

        for entry in self.data.values():
            username = str(entry.get("username", ""))
            user_id = str(entry.get("user_id", ""))
            entry_type = entry.get("last_type")

            if (
                application_type
                and entry_type != application_type
            ):
                continue

            if query:
                if (
                    query_lower not in username.lower()
                    and query != user_id
                ):
                    continue

            results.append(entry)

        if not results:
            await interaction.response.send_message(
                "🔎 Keine passenden Bewerber gefunden.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🔎 Bewerber gefunden",
            color=discord.Color.blurple(),
        )

        if application_type:
            config = get_type_data(application_type)

            if config:
                embed.description = (
                    f"Filter: {config['emoji']} "
                    f"**{config['name']}**"
                )

        for entry in results[:10]:
            entry_type = entry.get("last_type", "unbekannt")
            config = get_type_data(entry_type)

            type_name = (
                config["name"]
                if config
                else entry_type
            )

            status = entry.get("status", "unbekannt")
            last_application = entry.get("last_application")

            embed.add_field(
                name=(
                    f"👤 "
                    f"{entry.get('username', 'Unbekannt')}"
                ),
                value=(
                    f"🆔 `{entry.get('user_id')}`\n"
                    f"📋 **Bewerbung:** {type_name}\n"
                    f"📌 **Status:** {status}\n"
                    f"📅 **Letzte Bewerbung:** "
                    f"{format_date(last_application)}\n"
                    f"♾️ **Nächste Bewerbung:** Jetzt möglich\n"
                    f"📊 **Bewerbungen:** "
                    f"{entry.get('applications_count', 0)}"
                ),
                inline=False,
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # ========================================================
    # BEWERBERLISTE
    # ========================================================

    async def update_application_list(self, guild):
        channel = guild.get_channel(
            APPLICATION_LIST_CHANNEL_ID
        )

        if channel is None:
            return

        try:
            async for message in channel.history(limit=100):
                if (
                    self.bot.user
                    and message.author.id == self.bot.user.id
                ):
                    await message.delete()

        except Exception:
            logging.exception(
                "Alte Bewerberliste konnte nicht bereinigt werden."
            )

        embed = discord.Embed(
            title="📋 NexoriaCraft – Bewerberliste",
            description=(
                "Hier werden alle Bewerber gespeichert.\n\n"
                "Für eine gezielte Suche kannst du das "
                "**Bewerber-Suchsystem** benutzen.\n\n"
                "Die Liste zeigt immer die zuletzt bekannte "
                "Bewerbungsart und den aktuellen Status.\n\n"
                "♾️ Bewerbungen können jederzeit erneut erstellt werden."
            ),
            color=discord.Color.blurple(),
        )

        entries = list(self.data.values())

        if not entries:
            embed.add_field(
                name="Keine Bewerbungen",
                value=(
                    "Bisher wurden keine Bewerbungen gespeichert."
                ),
                inline=False,
            )
        else:
            entries.reverse()

            for entry in entries[:20]:
                entry_type = entry.get(
                    "last_type",
                    "unbekannt",
                )

                config = get_type_data(entry_type)

                type_name = (
                    config["name"]
                    if config
                    else entry_type
                )

                embed.add_field(
                    name=(
                        f"👤 "
                        f"{entry.get('username', 'Unbekannt')}"
                        f" • {type_name}"
                    ),
                    value=(
                        f"🆔 `{entry.get('user_id')}`\n"
                        f"📅 "
                        f"{format_date(entry.get('last_application'))}\n"
                        f"📌 "
                        f"{entry.get('status', 'unbekannt')}\n"
                        f"📊 "
                        f"{entry.get('applications_count', 0)} "
                        "Bewerbungen"
                    ),
                    inline=False,
                )

        embed.set_footer(
            text="NexoriaCraft • Bewerberverwaltung"
        )

        await channel.send(embed=embed)

    # ========================================================
    # SETUP
    # ========================================================

    async def cog_load(self):
        self.bot.add_view(ApplicationPanel())
        self.bot.add_view(SearchView())

    async def cog_unload(self):
        pass


# ============================================================
# SETUP FUNCTION
# ============================================================

async def setup(bot):
    await bot.add_cog(Applications(bot))
