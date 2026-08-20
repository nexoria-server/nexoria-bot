
import discord
from discord.ext import commands

import sqlite3
from datetime import datetime, timezone, timedelta


# ============================================================
# KONFIGURATION
# ============================================================

# Permanentes Team-Panel
TEAM_PANEL_CHANNEL_ID = 1527222155996041307

# Mod-Logs
MOD_LOG_CHANNEL_ID = 1527107932938965138

# Bestehende SQLite-Datenbank
DATABASE_FILE = "team_panel.db"


# ============================================================
# TEAM-ROLLEN
# ============================================================

TEAM_ROLES = [
    ("👑", "Owner", 1527101544351142128),
    ("👑", "Co-Owner", 1527112990758015016),
    ("🛡️", "Admin", 1527099723629203556),
    ("⚔️", "Moderator ++", 1527299075060404344),
    ("🔨", "Moderator", 1527099725369839756),
    ("💻", "Developer", 1527099942446039040),
    ("🏗️", "Builder", 1528052296099823808),
    ("🤝", "Supporter", 1527099685125492826),
    ("🛡️", "Test Supporter", 1527099612274364638),
    ("🎥", "Media", 1527099952730345574),
]


# ============================================================
# STERN-SYSTEM
# ============================================================

STARS_FOR_PROMOTION = 5

PROMOTION_ORDER = [
    1527099612274364638,  # Test Supporter
    1527099685125492826,  # Supporter
    1527099725369839756,  # Moderator
    1527299075060404344,  # Moderator ++
    1527099723629203556,  # Admin
]

# Wer Sterne vergeben / entfernen darf
STAR_GIVER_ROLES = {
    1527099723629203556,  # Admin
    1527112990758015016,  # Co-Owner
    1527101544351142128,  # Owner
}

# Wer das Team-Panel benutzen darf
TEAM_PANEL_ROLES = {
    1527099685125492826,  # Supporter
    1527099725369839756,  # Moderator
    1527299075060404344,  # Moderator ++
    1527099723629203556,  # Admin
    1527112990758015016,  # Co-Owner
    1527101544351142128,  # Owner
    1527099942446039040,  # Developer
    1528052296099823808,  # Builder
    1527099952730345574,  # Media
    1527099612274364638,  # Test Supporter
}

# Ban darf nur Admin+
BAN_ROLES = {
    1527099723629203556,  # Admin
    1527112990758015016,  # Co-Owner
    1527101544351142128,  # Owner
}


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def now():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def has_team_access(member: discord.Member):
    if member.guild_permissions.administrator:
        return True

    return any(
        role.id in TEAM_PANEL_ROLES
        for role in member.roles
    )


def can_manage_stars(member: discord.Member):
    if member.guild_permissions.administrator:
        return True

    return any(
        role.id in STAR_GIVER_ROLES
        for role in member.roles
    )


def can_manage_bans(member: discord.Member):
    if member.guild_permissions.administrator:
        return True

    return any(
        role.id in BAN_ROLES
        for role in member.roles
    )


# ============================================================
# DATENBANK
# ============================================================

class Database:

    def __init__(self):
        self.db = sqlite3.connect(
            DATABASE_FILE,
            check_same_thread=False
        )

        self.db.row_factory = sqlite3.Row

        self.create_tables()

    def create_tables(self):

        cursor = self.db.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                stars INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moderation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                duration TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        self.db.commit()

    # ========================================================
    # PLAYER
    # ========================================================

    def ensure_player(self, user_id):

        self.db.execute(
            """
            INSERT OR IGNORE INTO players
            (user_id, stars, created_at)
            VALUES (?, 0, ?)
            """,
            (
                user_id,
                now()
            )
        )

        self.db.commit()

    # ========================================================
    # STERNE
    # ========================================================

    def get_stars(self, user_id):

        self.ensure_player(user_id)

        row = self.db.execute(
            """
            SELECT stars
            FROM players
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if row:
            return row["stars"]

        return 0

    def set_stars(self, user_id, stars):

        self.ensure_player(user_id)

        self.db.execute(
            """
            UPDATE players
            SET stars = ?
            WHERE user_id = ?
            """,
            (
                stars,
                user_id
            )
        )

        self.db.commit()

    def add_star_history(
        self,
        user_id,
        moderator_id,
        amount,
        reason
    ):

        self.db.execute(
            """
            INSERT INTO stars
            (
                user_id,
                moderator_id,
                amount,
                reason,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                moderator_id,
                amount,
                reason,
                now()
            )
        )

        self.db.commit()

    def get_star_history(self, user_id):

        return self.db.execute(
            """
            SELECT *
            FROM stars
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (user_id,)
        ).fetchall()

    # ========================================================
    # MODERATION
    # ========================================================

    def add_moderation(
        self,
        user_id,
        moderator_id,
        action,
        reason,
        duration=None
    ):

        self.db.execute(
            """
            INSERT INTO moderation
            (
                user_id,
                moderator_id,
                action,
                reason,
                duration,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                moderator_id,
                action,
                reason,
                duration,
                now()
            )
        )

        self.db.commit()

    def get_history(self, user_id):

        return self.db.execute(
            """
            SELECT *
            FROM moderation
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,)
        ).fetchall()

    def count_action(self, user_id, action):

        row = self.db.execute(
            """
            SELECT COUNT(*) AS total
            FROM moderation
            WHERE user_id = ?
            AND action = ?
            """,
            (
                user_id,
                action
            )
        ).fetchone()

        return row["total"]

    # ========================================================
    # NOTIZEN
    # ========================================================

    def add_note(
        self,
        user_id,
        moderator_id,
        note
    ):

        self.db.execute(
            """
            INSERT INTO notes
            (
                user_id,
                moderator_id,
                note,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                moderator_id,
                note,
                now()
            )
        )

        self.db.commit()

    def get_notes(self, user_id):

        return self.db.execute(
            """
            SELECT *
            FROM notes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (user_id,)
        ).fetchall()


# ============================================================
# TEAM COG
# ============================================================

class Team(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.db = Database()
        self.panel_message_id = None

    # ========================================================
    # MOD LOG
    # ========================================================

    async def log(
        self,
        guild,
        title,
        description,
        color=discord.Color.blurple()
    ):

        if guild is None:
            return

        channel = guild.get_channel(
            MOD_LOG_CHANNEL_ID
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_footer(
            text="NexoriaCraft • Team Panel"
        )

        try:
            await channel.send(
                embed=embed
            )
        except discord.HTTPException:
            pass

    # ========================================================
    # TEAM PANEL EMBED
    # ========================================================

    def panel_embed(self):

        embed = discord.Embed(
            title="🛡️ NexoriaCraft Team Panel",
            description=(
                "**Willkommen im internen Team-Bereich.**\n\n"
                "Hier kann das Server-Team Spieler verwalten, "
                "Moderationsfälle bearbeiten, Teammitglieder "
                "verwalten und Statistiken einsehen.\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔎 **Spielerverwaltung**\n"
                "Spieler suchen und vollständige Profile anzeigen.\n\n"
                "⚖️ **Moderation**\n"
                "Warnungen, Timeouts, Kicks und Bans verwalten.\n\n"
                "⭐ **Team-System**\n"
                "Sterne vergeben und automatische Beförderungen.\n\n"
                "👮 **Team**\n"
                "Teammitglieder und aktuelle Ränge anzeigen.\n\n"
                "📊 **Statistiken**\n"
                "Moderations- und Teamstatistiken anzeigen.\n\n"
                "📝 **Notizen**\n"
                "Interne Notizen zu Spielern speichern.\n\n"
                "📜 **Verlauf**\n"
                "Moderationsverlauf eines Spielers anzeigen."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🔐 Berechtigungen",
            value=(
                "Alle Teammitglieder können das Panel und "
                "die normalen Moderationsfunktionen benutzen.\n\n"
                "⭐ **Sterne:** Admin / Co-Owner / Owner\n"
                "🔨 **Bans:** Admin / Co-Owner / Owner"
            ),
            inline=False
        )

        embed.set_footer(
            text="NexoriaCraft • Team Panel • Dauerhaft"
        )

        return embed

    # ========================================================
    # PERMANENTES PANEL
    # ========================================================

    async def setup_panel(self, guild):

        channel = guild.get_channel(
            TEAM_PANEL_CHANNEL_ID
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            print(
                "[TEAM] Team-Panel-Kanal nicht gefunden."
            )
            return

        # Vorhandene Panel-Nachricht suchen
        try:

            async for message in channel.history(
                limit=100
            ):

                if (
                    message.author.id == self.bot.user.id
                    and message.embeds
                    and message.embeds[0].title
                    == "🛡️ NexoriaCraft Team Panel"
                ):

                    self.panel_message_id = message.id

                    try:
                        await message.edit(
                            embed=self.panel_embed(),
                            view=MainPanelView(self)
                        )
                    except discord.HTTPException:
                        pass

                    print(
                        f"[TEAM] Vorhandenes Panel aktualisiert: {message.id}"
                    )

                    return

        except discord.HTTPException as error:

            print(
                f"[TEAM] Fehler beim Durchsuchen des Kanals: {error}"
            )

            return

        # Neue Panel-Nachricht
        try:

            message = await channel.send(
                embed=self.panel_embed(),
                view=MainPanelView(self)
            )

            self.panel_message_id = message.id

            print(
                f"[TEAM] Neues Panel erstellt: {message.id}"
            )

        except discord.HTTPException as error:

            print(
                f"[TEAM] Panel konnte nicht erstellt werden: {error}"
            )

    # ========================================================
    # START
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(self):

        # Persistent View registrieren
        self.bot.add_view(
            MainPanelView(self)
        )

        for guild in self.bot.guilds:
            await self.setup_panel(guild)

    # ========================================================
    # TEAMLISTE
    # ========================================================

    async def team_embed(self, guild):

        embed = discord.Embed(
            title="👮 NexoriaCraft Team",
            description="Aktuelles Server-Team.",
            color=discord.Color.blurple()
        )

        for emoji, name, role_id in TEAM_ROLES:

            role = guild.get_role(role_id)

            if role is None:

                value = "⚠️ Rolle nicht gefunden."

            else:

                members = [
                    member
                    for member in role.members
                    if not member.bot
                ]

                if members:

                    members.sort(
                        key=lambda x:
                        x.display_name.lower()
                    )

                    value = "\n".join(
                        f"• {member.mention}"
                        for member in members
                    )

                else:

                    value = "-"

            embed.add_field(
                name=f"{emoji} {name}",
                value=value,
                inline=False
            )

        embed.set_footer(
            text="NexoriaCraft • Teamliste"
        )

        return embed

    # ========================================================
    # SPIELERPROFIL
    # ========================================================

    async def player_embed(
        self,
        guild,
        member
    ):

        warnings = self.db.count_action(
            member.id,
            "Warnung"
        )

        mutes = self.db.count_action(
            member.id,
            "Timeout"
        )

        kicks = self.db.count_action(
            member.id,
            "Kick"
        )

        bans = self.db.count_action(
            member.id,
            "Ban"
        )

        stars = self.db.get_stars(
            member.id
        )

        roles = [
            role.mention
            for role in member.roles
            if role != guild.default_role
        ]

        if roles:
            role_text = " ".join(
                roles[-15:]
            )
        else:
            role_text = "-"

        status = (
            "🟢 Online"
            if member.status != discord.Status.offline
            else "⚫ Offline"
        )

        embed = discord.Embed(
            title="👤 Spielerprofil",
            description=(
                f"**{member.display_name}**\n"
                f"{member.mention}\n"
                f"🆔 `{member.id}`\n\n"
                f"{status}"
            ),
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="📅 Account erstellt",
            value=discord.utils.format_dt(
                member.created_at,
                "F"
            ),
            inline=False
        )

        if member.joined_at:

            embed.add_field(
                name="📅 Serverbeitritt",
                value=discord.utils.format_dt(
                    member.joined_at,
                    "F"
                ),
                inline=False
            )

        embed.add_field(
            name="🎭 Rollen",
            value=role_text,
            inline=False
        )

        embed.add_field(
            name="⭐ Team-Sterne",
            value=f"{stars}/{STARS_FOR_PROMOTION}",
            inline=True
        )

        embed.add_field(
            name="⚠️ Warnungen",
            value=str(warnings),
            inline=True
        )

        embed.add_field(
            name="🔇 Timeouts",
            value=str(mutes),
            inline=True
        )

        embed.add_field(
            name="👢 Kicks",
            value=str(kicks),
            inline=True
        )

        embed.add_field(
            name="🔨 Bans",
            value=str(bans),
            inline=True
        )

        embed.set_footer(
            text="NexoriaCraft • Spielerprofil"
        )

        return embed

    # ========================================================
    # BEFÖRDERUNG
    # ========================================================

    async def promote(
        self,
        guild,
        member
    ):

        current_index = None

        for index, role_id in enumerate(
            PROMOTION_ORDER
        ):

            if member.get_role(role_id):

                current_index = index
                break

        # Kein Beförderungsrang
        if current_index is None:
            return False

        # Bereits höchster Rang
        if current_index >= len(
            PROMOTION_ORDER
        ) - 1:
            return False

        old_role = guild.get_role(
            PROMOTION_ORDER[current_index]
        )

        new_role = guild.get_role(
            PROMOTION_ORDER[current_index + 1]
        )

        if not old_role or not new_role:
            return False

        try:

            await member.remove_roles(
                old_role,
                reason="5 Team-Sterne erreicht"
            )

            await member.add_roles(
                new_role,
                reason="Automatische Beförderung"
            )

        except discord.Forbidden:

            await self.log(
                guild,
                "❌ Beförderung fehlgeschlagen",
                (
                    f"**Teammitglied:** {member.mention}\n"
                    f"**Von:** {old_role.mention}\n"
                    f"**Zu:** {new_role.mention}\n\n"
                    "Der Bot besitzt keine ausreichende "
                    "Rollenberechtigung."
                ),
                discord.Color.red()
            )

            return False

        self.db.set_stars(
            member.id,
            0
        )

        await self.log(
            guild,
            "🎉 Automatische Beförderung",
            (
                f"**Teammitglied:** {member.mention}\n"
                f"**Alter Rang:** {old_role.mention}\n"
                f"**Neuer Rang:** {new_role.mention}\n\n"
                "⭐ 5 Sterne erreicht."
            ),
            discord.Color.green()
        )

        try:

            await member.send(
                "🎉 **Herzlichen Glückwunsch!**\n\n"
                f"Du wurdest von **{old_role.name}** "
                f"zu **{new_role.name}** befördert.\n\n"
                "Grund: Du hast 5 ⭐ Team-Sterne erreicht."
            )

        except discord.HTTPException:
            pass

        return True

    # ========================================================
    # STERN VERGEBEN
    # ========================================================

    async def give_star(
        self,
        interaction,
        target,
        reason
    ):

        if not can_manage_stars(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du darfst keine Team-Sterne vergeben.",
                ephemeral=True
            )

            return

        # Nur Teammitglieder sollen Sterne erhalten
        if not has_team_access(target):

            await interaction.response.send_message(
                "❌ Sterne können nur an Teammitglieder "
                "vergeben werden.",
                ephemeral=True
            )

            return

        stars = self.db.get_stars(
            target.id
        )

        if stars >= STARS_FOR_PROMOTION:

            await interaction.response.send_message(
                "❌ Dieses Teammitglied hat bereits "
                "genug Sterne für eine Beförderung.",
                ephemeral=True
            )

            return

        stars += 1

        self.db.set_stars(
            target.id,
            stars
        )

        self.db.add_star_history(
            target.id,
            interaction.user.id,
            1,
            reason
        )

        await self.log(
            interaction.guild,
            "⭐ Team-Stern vergeben",
            (
                f"**Teammitglied:** {target.mention}\n"
                f"**Von:** {interaction.user.mention}\n"
                f"**Grund:** {reason}\n\n"
                f"⭐ Fortschritt: "
                f"**{stars}/{STARS_FOR_PROMOTION}**"
            ),
            discord.Color.gold()
        )

        promoted = False

        if stars >= STARS_FOR_PROMOTION:

            promoted = await self.promote(
                interaction.guild,
                target
            )

        if promoted:

            message = (
                "🎉 **5 Sterne erreicht!**\n"
                "Das Teammitglied wurde automatisch befördert."
            )

        else:

            message = (
                f"⭐ Stern vergeben.\n\n"
                f"**{target.display_name}** hat jetzt "
                f"**{stars}/{STARS_FOR_PROMOTION}** Sterne."
            )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )

    # ========================================================
    # STERN ENTFERNEN
    # ========================================================

    async def remove_star(
        self,
        interaction,
        target,
        reason
    ):

        if not can_manage_stars(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du darfst keine Team-Sterne entfernen.",
                ephemeral=True
            )

            return

        stars = self.db.get_stars(
            target.id
        )

        if stars <= 0:

            await interaction.response.send_message(
                "❌ Dieses Teammitglied hat keine Sterne.",
                ephemeral=True
            )

            return

        stars -= 1

        self.db.set_stars(
            target.id,
            stars
        )

        self.db.add_star_history(
            target.id,
            interaction.user.id,
            -1,
            reason
        )

        await self.log(
            interaction.guild,
            "⭐ Team-Stern entfernt",
            (
                f"**Teammitglied:** {target.mention}\n"
                f"**Von:** {interaction.user.mention}\n"
                f"**Grund:** {reason}\n\n"
                f"⭐ Neuer Stand: "
                f"**{stars}/{STARS_FOR_PROMOTION}**"
            ),
            discord.Color.orange()
        )

        await interaction.response.send_message(
            (
                "⭐ Stern entfernt.\n\n"
                f"**{target.display_name}** hat jetzt "
                f"**{stars}/{STARS_FOR_PROMOTION}** Sterne."
            ),
            ephemeral=True
        )


# ============================================================
# SPIELERSUCHE
# ============================================================

class SearchModal(
    discord.ui.Modal,
    title="🔎 Spieler suchen"
):

    query = discord.ui.TextInput(
        label="Name oder Discord-ID",
        placeholder="z.B. Luca oder 123456789012345678",
        required=True,
        max_length=100
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if not guild:
            return

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keinen Zugriff auf das Team Panel.",
                ephemeral=True
            )

            return

        search = self.query.value.strip().lower()

        member = None

        # Suche per ID
        if search.isdigit():

            member = guild.get_member(
                int(search)
            )

        # Suche per Name
        if member is None:

            matches = [
                member
                for member in guild.members
                if (
                    search in member.name.lower()
                    or search in member.display_name.lower()
                    or (
                        member.global_name
                        and search in member.global_name.lower()
                    )
                )
                and not member.bot
            ]

            if len(matches) == 1:

                member = matches[0]

            elif len(matches) > 1:

                options = []

                for matched_member in matches[:25]:

                    options.append(
                        discord.SelectOption(
                            label=matched_member.display_name[:100],
                            value=str(matched_member.id),
                            description=str(
                                matched_member.id
                            )
                        )
                    )

                await interaction.response.send_message(
                    "🔎 Mehrere Spieler gefunden:",
                    view=SearchResultsView(
                        self.cog,
                        options
                    ),
                    ephemeral=True
                )

                return

        if member is None:

            await interaction.response.send_message(
                "❌ Kein Spieler gefunden.",
                ephemeral=True
            )

            return

        await show_player(
            interaction,
            self.cog,
            member
        )


# ============================================================
# SUCHERGEBNISSE
# ============================================================

class SearchResultsView(
    discord.ui.View
):

    def __init__(
        self,
        cog,
        options
    ):

        super().__init__(
            timeout=120
        )

        self.add_item(
            SearchSelect(
                cog,
                options
            )
        )


class SearchSelect(
    discord.ui.Select
):

    def __init__(
        self,
        cog,
        options
    ):

        super().__init__(
            placeholder="Spieler auswählen...",
            options=options
        )

        self.cog = cog

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        member = interaction.guild.get_member(
            int(self.values[0])
        )

        if member is None:

            await interaction.response.send_message(
                "❌ Spieler nicht mehr auf dem Server.",
                ephemeral=True
            )

            return

        await show_player(
            interaction,
            self.cog,
            member
        )


# ============================================================
# SPIELER PROFIL ANZEIGEN
# ============================================================

async def show_player(
    interaction,
    cog,
    member
):

    if not has_team_access(
        interaction.user
    ):

        await interaction.response.send_message(
            "❌ Keine Berechtigung.",
            ephemeral=True
        )

        return

    embed = await cog.player_embed(
        interaction.guild,
        member
    )

    await interaction.response.send_message(
        embed=embed,
        view=PlayerView(
            cog,
            member
        ),
        ephemeral=True
    )


# ============================================================
# MODERATION MODAL
# ============================================================

class ModerationModal(
    discord.ui.Modal
):

    reason = discord.ui.TextInput(
        label="Grund",
        placeholder="Grund der Aktion...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    def __init__(
        self,
        cog,
        target,
        action
    ):

        super().__init__(
            title=f"{action} • {target.display_name}"
        )

        self.cog = cog
        self.target = target
        self.action = action

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if not guild:

            await interaction.response.send_message(
                "❌ Server nicht gefunden.",
                ephemeral=True
            )

            return

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        # Ban nur Admin+
        if (
            self.action == "Ban"
            and not can_manage_bans(
                interaction.user
            )
        ):

            await interaction.response.send_message(
                "❌ Nur Admins, Co-Owner oder Owner "
                "dürfen bannen.",
                ephemeral=True
            )

            return

        # Server-Owner schützen
        if self.target == guild.owner:

            await interaction.response.send_message(
                "❌ Der Server-Owner kann nicht moderiert werden.",
                ephemeral=True
            )

            return

        # Selbstmoderation verhindern
        if self.target == interaction.user:

            await interaction.response.send_message(
                "❌ Du kannst dich nicht selbst moderieren.",
                ephemeral=True
            )

            return

        try:

            # =================================================
            # WARNUNG
            # =================================================

            if self.action == "Warnung":

                self.cog.db.add_moderation(
                    self.target.id,
                    interaction.user.id,
                    "Warnung",
                    self.reason.value
                )

            # =================================================
            # TIMEOUT
            # =================================================

            elif self.action == "Timeout":

                await self.target.timeout(
                    timedelta(minutes=10),
                    reason=self.reason.value
                )

                self.cog.db.add_moderation(
                    self.target.id,
                    interaction.user.id,
                    "Timeout",
                    self.reason.value,
                    "10 Minuten"
                )

            # =================================================
            # KICK
            # =================================================

            elif self.action == "Kick":

                await self.target.kick(
                    reason=self.reason.value
                )

                self.cog.db.add_moderation(
                    self.target.id,
                    interaction.user.id,
                    "Kick",
                    self.reason.value
                )

            # =================================================
            # BAN
            # =================================================

            elif self.action == "Ban":

                await self.target.ban(
                    reason=self.reason.value
                )

                self.cog.db.add_moderation(
                    self.target.id,
                    interaction.user.id,
                    "Ban",
                    self.reason.value
                )

            else:

                await interaction.response.send_message(
                    "❌ Unbekannte Aktion.",
                    ephemeral=True
                )

                return

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot darf diese Aktion nicht "
                "durchführen. Prüfe seine Rollenposition "
                "und Discord-Berechtigungen.",
                ephemeral=True
            )

            return

        except discord.HTTPException as error:

            await interaction.response.send_message(
                f"❌ Discord-Fehler: `{error}`",
                ephemeral=True
            )

            return

        await self.cog.log(
            guild,
            f"⚖️ {self.action}",
            (
                f"**Spieler:** {self.target.mention}\n"
                f"**Moderator:** {interaction.user.mention}\n"
                f"**Grund:** {self.reason.value}"
            ),
            discord.Color.orange()
        )

        await interaction.response.send_message(
            f"✅ **{self.action}** wurde durchgeführt.",
            ephemeral=True
        )


# ============================================================
# NOTIZ MODAL
# ============================================================

class NoteModal(
    discord.ui.Modal,
    title="📝 Interne Notiz"
):

    note = discord.ui.TextInput(
        label="Notiz",
        placeholder="Interne Team-Notiz...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    def __init__(
        self,
        cog,
        target
    ):

        super().__init__()

        self.cog = cog
        self.target = target

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        self.cog.db.add_note(
            self.target.id,
            interaction.user.id,
            self.note.value
        )

        await self.cog.log(
            interaction.guild,
            "📝 Interne Notiz",
            (
                f"**Spieler:** {self.target.mention}\n"
                f"**Teammitglied:** {interaction.user.mention}\n\n"
                f"**Notiz:**\n{self.note.value}"
            )
        )

        await interaction.response.send_message(
            "✅ Interne Notiz gespeichert.",
            ephemeral=True
        )


# ============================================================
# STERN MODAL
# ============================================================

class StarModal(
    discord.ui.Modal,
    title="⭐ Team-Stern vergeben"
):

    reason = discord.ui.TextInput(
        label="Grund",
        placeholder="Warum bekommt das Teammitglied einen Stern?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(
        self,
        cog,
        target
    ):

        super().__init__()

        self.cog = cog
        self.target = target

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        await self.cog.give_star(
            interaction,
            self.target,
            self.reason.value
        )


# ============================================================
# STERN ENTFERNEN MODAL
# ============================================================

class RemoveStarModal(
    discord.ui.Modal,
    title="⭐ Team-Stern entfernen"
):

    reason = discord.ui.TextInput(
        label="Grund",
        placeholder="Warum wird der Stern entfernt?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(
        self,
        cog,
        target
    ):

        super().__init__()

        self.cog = cog
        self.target = target

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        await self.cog.remove_star(
            interaction,
            self.target,
            self.reason.value
        )


# ============================================================
# NOTIZEN ANZEIGEN
# ============================================================

async def show_notes(
    interaction,
    cog,
    target
):

    notes = cog.db.get_notes(
        target.id
    )

    if not notes:

        text = "Keine internen Notizen vorhanden."

    else:

        lines = []

        for row in notes:

            lines.append(
                f"**📝 {row['created_at']}**\n"
                f"{row['note']}\n"
                f"👮 <@{row['moderator_id']}>"
            )

        text = "\n\n".join(lines)

    # Discord Embed Description max. 4096 Zeichen
    if len(text) > 4000:
        text = text[:4000] + "\n..."

    embed = discord.Embed(
        title=f"📝 Interne Notizen • {target.display_name}",
        description=text,
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# SPIELER VIEW
# ============================================================

class PlayerView(
    discord.ui.View
):

    def __init__(
        self,
        cog,
        target
    ):

        super().__init__(
            timeout=300
        )

        self.cog = cog
        self.target = target

    # ========================================================
    # WARNUNG
    # ========================================================

    @discord.ui.button(
        label="Warnung",
        emoji="⚠️",
        style=discord.ButtonStyle.secondary,
        custom_id="nexoria_player_warning"
    )
    async def warning(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            ModerationModal(
                self.cog,
                self.target,
                "Warnung"
            )
        )

    # ========================================================
    # TIMEOUT
    # ========================================================

    @discord.ui.button(
        label="Timeout",
        emoji="🔇",
        style=discord.ButtonStyle.secondary,
        custom_id="nexoria_player_timeout"
    )
    async def timeout_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            ModerationModal(
                self.cog,
                self.target,
                "Timeout"
            )
        )

    # ========================================================
    # KICK
    # ========================================================

    @discord.ui.button(
        label="Kick",
        emoji="👢",
        style=discord.ButtonStyle.danger,
        custom_id="nexoria_player_kick"
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            ModerationModal(
                self.cog,
                self.target,
                "Kick"
            )
        )

    # ========================================================
    # BAN
    # ========================================================

    @discord.ui.button(
        label="Ban",
        emoji="🔨",
        style=discord.ButtonStyle.danger,
        custom_id="nexoria_player_ban"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not can_manage_bans(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Nur Admins, Co-Owner oder Owner "
                "dürfen bannen.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            ModerationModal(
                self.cog,
                self.target,
                "Ban"
            )
        )

    # ========================================================
    # NOTIZ
    # ========================================================

    @discord.ui.button(
        label="Notiz",
        emoji="📝",
        style=discord.ButtonStyle.secondary,
        custom_id="nexoria_player_note"
    )
    async def note(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            NoteModal(
                self.cog,
                self.target
            )
        )

    # ========================================================
    # NOTIZEN ANZEIGEN
    # ========================================================

    @discord.ui.button(
        label="Notizen",
        emoji="📋",
        style=discord.ButtonStyle.secondary,
        custom_id="nexoria_player_notes"
    )
    async def notes(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await show_notes(
            interaction,
            self.cog,
            self.target
        )

    # ========================================================
    # STERN VERGEBEN
    # ========================================================

    @discord.ui.button(
        label="Stern",
        emoji="⭐",
        style=discord.ButtonStyle.success,
        custom_id="nexoria_player_star"
    )
    async def star(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not can_manage_stars(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Nur Admins, Co-Owner oder Owner "
                "dürfen Sterne vergeben.",
                ephemeral=True
            )

            return

        if not has_team_access(
            self.target
        ):

            await interaction.response.send_message(
                "❌ Sterne können nur an "
                "Teammitglieder vergeben werden.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            StarModal(
                self.cog,
                self.target
            )
        )

    # ========================================================
    # STERN ENTFERNEN
    # ========================================================

    @discord.ui.button(
        label="Stern -",
        emoji="➖",
        style=discord.ButtonStyle.danger,
        custom_id="nexoria_player_remove_star"
    )
    async def remove_star(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not can_manage_stars(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Nur Admins, Co-Owner oder Owner "
                "dürfen Sterne entfernen.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            RemoveStarModal(
                self.cog,
                self.target
            )
        )

    # ========================================================
    # VERLAUF
    # ========================================================

    @discord.ui.button(
        label="Verlauf",
        emoji="📜",
        style=discord.ButtonStyle.primary,
        custom_id="nexoria_player_history"
    )
    async def history(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        history = self.cog.db.get_history(
            self.target.id
        )

        if not history:

            text = (
                "Keine Moderationsaktionen vorhanden."
            )

        else:

            lines = []

            for row in history:

                duration = ""

                if row["duration"]:
                    duration = (
                        f"\nDauer: {row['duration']}"
                    )

                lines.append(
                    f"**{row['action']}** • "
                    f"{row['created_at']}\n"
                    f"Grund: {row['reason']}"
                    f"{duration}\n"
                    f"Moderator: <@{row['moderator_id']}>"
                )

            text = "\n\n".join(lines)

        # Discord Embed Description max. 4096 Zeichen
        if len(text) > 4000:
            text = text[:4000] + "\n..."

        embed = discord.Embed(
            title=(
                f"📜 Moderationsverlauf • "
                f"{self.target.display_name}"
            ),
            description=text,
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ============================================================
# HAUPTPANEL
# ============================================================

class MainPanelView(
    discord.ui.View
):

    def __init__(self, cog):

        # None = dauerhaft / persistent
        super().__init__(
            timeout=None
        )

        self.cog = cog

    # ========================================================
    # SPIELER SUCHEN
    # ========================================================

    @discord.ui.button(
        label="Spieler suchen",
        emoji="🔎",
        style=discord.ButtonStyle.primary,
        custom_id="nexoria_team_search"
    )
    async def search(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keinen Zugriff auf das Team Panel.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            SearchModal(
                self.cog
            )
        )

    # ========================================================
    # TEAM
    # ========================================================

    @discord.ui.button(
        label="Team",
        emoji="👮",
        style=discord.ButtonStyle.secondary,
        custom_id="nexoria_team_members"
    )
    async def team(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        embed = await self.cog.team_embed(
            interaction.guild
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # ========================================================
    # STATISTIKEN
    # ========================================================

    @discord.ui.button(
        label="Statistiken",
        emoji="📊",
        style=discord.ButtonStyle.secondary,
        custom_id="nexoria_team_stats"
    )
    async def stats(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not has_team_access(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        db = self.cog.db

        warnings = db.db.execute(
            """
            SELECT COUNT(*) AS total
            FROM moderation
            WHERE action = 'Warnung'
            """
        ).fetchone()["total"]

        timeouts = db.db.execute(
            """
            SELECT COUNT(*) AS total
            FROM moderation
            WHERE action = 'Timeout'
            """
        ).fetchone()["total"]

        kicks = db.db.execute(
            """
            SELECT COUNT(*) AS total
            FROM moderation
            WHERE action = 'Kick'
            """
        ).fetchone()["total"]

        bans = db.db.execute(
            """
            SELECT COUNT(*) AS total
            FROM moderation
            WHERE action = 'Ban'
            """
        ).fetchone()["total"]

        total_stars = db.db.execute(
            """
            SELECT COALESCE(SUM(stars), 0) AS total
            FROM players
            """
        ).fetchone()["total"]

        total_notes = db.db.execute(
            """
            SELECT COUNT(*) AS total
            FROM notes
            """
        ).fetchone()["total"]

        embed = discord.Embed(
            title="📊 Team-Statistiken",
            description="Gesamte Team- und Moderationsstatistik.",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="⚠️ Warnungen",
            value=str(warnings),
            inline=True
        )

        embed.add_field(
            name="🔇 Timeouts",
            value=str(timeouts),
            inline=True
        )

        embed.add_field(
            name="👢 Kicks",
            value=str(kicks),
            inline=True
        )

        embed.add_field(
            name="🔨 Bans",
            value=str(bans),
            inline=True
        )

        embed.add_field(
            name="⭐ Team-Sterne",
            value=str(total_stars),
            inline=True
        )

        embed.add_field(
            name="📝 Notizen",
            value=str(total_notes),
            inline=True
        )

        embed.set_footer(
            text="NexoriaCraft • Team-Statistiken"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # ========================================================
    # TEAM-STERNE
    # ========================================================

    @discord.ui.button(
        label="Team-Sterne",
        emoji="⭐",
        style=discord.ButtonStyle.success,
        custom_id="nexoria_team_stars"
    )
    async def stars(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not can_manage_stars(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Nur Admins, Co-Owner und Owner "
                "dürfen Team-Sterne verwalten.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "⭐ Öffne über **🔎 Spieler suchen** "
            "das Teammitglied und wähle anschließend "
            "**⭐ Stern** oder **➖ Stern -**.",
            ephemeral=True
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Team(bot)
    )

