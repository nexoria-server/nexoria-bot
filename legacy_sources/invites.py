import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# KONFIGURATION
# ============================================================

INVITE_PANEL_CHANNEL_ID = 1527111245998854335

# Wenn du eine eigene Kategorie für Invite-Claim-Tickets hast,
# hier die ID eintragen.
#
# 0 = Kategorie des Invite-Panels verwenden.
CLAIM_CATEGORY_ID = 0

DATA_FILE = Path("invites.json")


# ============================================================
# BELOHNUNGEN
# ============================================================

REWARDS = {
    5: {
        "name": "5 Invites",
        "emoji": "🎁",
        "description": "1x Vote-Key",
    },

    10: {
        "name": "10 Invites",
        "emoji": "🔑",
        "description": "2x Rare Key",
    },

    15: {
        "name": "15 Invites",
        "emoji": "💎",
        "description": "3x Rare Key",
    },

    25: {
        "name": "25 Invites",
        "emoji": "🏆",
        "description": "5x Rare Key + kleine Ingame-Belohnung",
    },

    35: {
        "name": "35 Invites",
        "emoji": "🔥",
        "description": "7x Rare Key + besondere Ingame-Belohnung",
    },

    50: {
        "name": "50 Invites",
        "emoji": "👑",
        "description": "10x Rare Key + exklusive Discord-Rolle",
    },
}


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def utcnow():
    return datetime.now(timezone.utc)


def load_data():
    if not DATA_FILE.exists():
        return {
            "users": {},
            "invites": {},
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        data.setdefault("users", {})
        data.setdefault("invites", {})

        return data

    except Exception:
        logging.exception("invites.json konnte nicht gelesen werden.")

        return {
            "users": {},
            "invites": {},
        }


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4,
        )


def get_user_data(data, user_id):
    user_id = str(user_id)

    if user_id not in data["users"]:
        data["users"][user_id] = {
            "username": "",
            "invites": 0,
            "joins": [],
            "left": 0,
            "claimed_rewards": [],
            "created_invites": [],
        }

    return data["users"][user_id]


def reward_available(user_data, amount):
    return (
        user_data.get("invites", 0) >= amount
        and amount not in user_data.get(
            "claimed_rewards",
            [],
        )
    )


def next_reward(user_data):
    invites = user_data.get("invites", 0)
    claimed = user_data.get("claimed_rewards", [])

    for amount in sorted(REWARDS):
        if amount > invites:
            return amount

        if amount not in claimed:
            return amount

    return None


# ============================================================
# CLAIM-MODAL
# ============================================================

class ClaimModal(discord.ui.Modal):
    def __init__(self, reward_amount):
        self.reward_amount = reward_amount

        reward = REWARDS[reward_amount]

        super().__init__(
            title=f"Belohnung claimen – {reward['name']}"
        )

        self.minecraft_name = discord.ui.TextInput(
            label="Minecraft-Name",
            placeholder="Dein Minecraft-Name",
            required=True,
            max_length=32,
        )

        self.add_item(self.minecraft_name)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Invites")

        if cog is None:
            await interaction.response.send_message(
                "❌ Das Invite-System ist momentan nicht verfügbar.",
                ephemeral=True,
            )
            return

        await cog.create_claim_ticket(
            interaction,
            self.reward_amount,
            self.minecraft_name.value.strip(),
        )


# ============================================================
# INVITE PANEL
# ============================================================

class InvitePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Invite erstellen",
        emoji="🔗",
        style=discord.ButtonStyle.primary,
        custom_id="invites_create",
    )
    async def create_invite(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        cog = interaction.client.get_cog("Invites")

        if cog is None:
            await interaction.response.send_message(
                "❌ Invite-System nicht verfügbar.",
                ephemeral=True,
            )
            return

        await cog.create_invite(interaction)

    @discord.ui.button(
        label="Meine Invites",
        emoji="📊",
        style=discord.ButtonStyle.secondary,
        custom_id="invites_stats",
    )
    async def stats(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        cog = interaction.client.get_cog("Invites")

        if cog is None:
            return

        await cog.show_stats(interaction)

    @discord.ui.button(
        label="Belohnungen",
        emoji="🎁",
        style=discord.ButtonStyle.success,
        custom_id="invites_rewards",
    )
    async def rewards(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        cog = interaction.client.get_cog("Invites")

        if cog is None:
            return

        await cog.show_rewards(interaction)

    @discord.ui.button(
        label="Belohnung claimen",
        emoji="🎫",
        style=discord.ButtonStyle.success,
        custom_id="invites_claim",
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        cog = interaction.client.get_cog("Invites")

        if cog is None:
            return

        await cog.show_claim_menu(interaction)


# ============================================================
# ADMIN SUCHE
# ============================================================

class AdminSearchModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Invite-Spieler suchen"
        )

        self.search = discord.ui.TextInput(
            label="Discord-Name oder User-ID",
            placeholder="z. B. Luca oder 123456789",
            required=True,
            max_length=100,
        )

        self.add_item(self.search)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren können diese Suche benutzen.",
                ephemeral=True,
            )
            return

        cog = interaction.client.get_cog("Invites")

        if cog is None:
            return

        await cog.search_player(
            interaction,
            self.search.value.strip(),
        )


class AdminSearchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Spieler suchen",
        emoji="🔎",
        style=discord.ButtonStyle.primary,
        custom_id="invites_admin_search",
    )
    async def search(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Nur Administratoren dürfen diese Funktion benutzen.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            AdminSearchModal()
        )


# ============================================================
# CLAIM AUSWÄHLEN
# ============================================================

class RewardSelect(discord.ui.Select):
    def __init__(self, cog):
        self.cog = cog

        options = []

        for amount, reward in REWARDS.items():
            options.append(
                discord.SelectOption(
                    label=reward["name"],
                    description=reward["description"][:100],
                    emoji=reward["emoji"],
                    value=str(amount),
                )
            )

        super().__init__(
            placeholder="Wähle eine Belohnung...",
            options=options,
            custom_id="invites_reward_select",
        )

    async def callback(self, interaction: discord.Interaction):
        amount = int(self.values[0])

        user_data = get_user_data(
            self.cog.data,
            interaction.user.id,
        )

        if not reward_available(
            user_data,
            amount,
        ):
            await interaction.response.send_message(
                "❌ Diese Belohnung kannst du noch nicht "
                "claimen oder du hast sie bereits erhalten.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            ClaimModal(amount)
        )


class ClaimView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(
            timeout=120
        )

        self.add_item(
            RewardSelect(cog)
        )


# ============================================================
# COG
# ============================================================

class Invites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

        # Discord Invite-Code -> Invite-Daten
        self.invite_cache = {}

        # User-ID -> Invite-Code
        self.member_invites = {}

    # ========================================================
    # PANEL POSTEN
    # ========================================================

    @app_commands.command(
        name="invite_panel",
        description="Postet das Invite-System.",
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def invite_panel(
        self,
        interaction: discord.Interaction,
    ):
        channel = interaction.guild.get_channel(
            INVITE_PANEL_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Invite-Kanal wurde nicht gefunden.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🎟️ NexoriaCraft – Invite-System",
            description=(
                "## 👋 Willkommen beim Invite-System!\n\n"
                "Du möchtest dir durch das Einladen neuer "
                "Spieler **Discord- und Ingame-Belohnungen** "
                "verdienen?\n\n"

                "Dann bist du hier richtig.\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                "### 🔗 So funktioniert es\n\n"

                "1. Klicke auf **Invite erstellen**.\n"
                "2. Der Bot erstellt deinen persönlichen "
                "Invite-Link.\n"
                "3. Schicke den Link an deine Freunde.\n"
                "4. Wenn sie dem Server beitreten, wird der "
                "Invite deinem Konto gutgeschrieben.\n"
                "5. Sammle genügend Invites und hole dir "
                "deine Belohnungen.\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                "### ⏳ Wichtig\n\n"

                "Jeder über dieses System erstellte Invite ist "
                "**2 Tage gültig**.\n\n"

                "Nach Ablauf wird der Invite automatisch "
                "ungültig und vom System entfernt.\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                "### 🎁 Belohnungen\n\n"

                "🎁 **5 Invites** → 1x Vote-Key\n"
                "🔑 **10 Invites** → 2x Rare Key\n"
                "💎 **15 Invites** → 3x Rare Key\n"
                "🏆 **25 Invites** → 5x Rare Key + Ingame-Belohnung\n"
                "🔥 **35 Invites** → 7x Rare Key + besondere Belohnung\n"
                "👑 **50 Invites** → 10x Rare Key + exklusive Belohnung\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                "### 🎫 Belohnung einlösen\n\n"

                "Sobald du eine Belohnung erreicht hast, "
                "kannst du über **Belohnung claimen** ein "
                "Ticket eröffnen.\n\n"

                "Das Team prüft anschließend deine Invites "
                "und stellt dir die entsprechende Belohnung "
                "bereit.\n\n"

                "⚠️ **Keine Self-Invites oder Fake-Accounts.**\n"
                "Missbrauch des Systems kann zum Ausschluss "
                "von den Belohnungen führen."
            ),
            color=discord.Color.blurple(),
        )

        embed.set_footer(
            text="NexoriaCraft • Invite Rewards"
        )

        await channel.send(
            embed=embed,
            view=InvitePanelView(),
        )

        await interaction.response.send_message(
            f"✅ Invite-Panel wurde in {channel.mention} gepostet.",
            ephemeral=True,
        )

    # ========================================================
    # ADMIN PANEL
    # ========================================================

    @app_commands.command(
        name="invite_admin",
        description="Postet die Invite-Verwaltung.",
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def invite_admin(
        self,
        interaction: discord.Interaction,
    ):
        channel = interaction.guild.get_channel(
            INVITE_PANEL_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Kanal nicht gefunden.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🔎 Invite-Verwaltung",
            description=(
                "Hier können Administratoren Spieler "
                "nachschlagen.\n\n"

                "Mit der Suche kannst du sehen:\n\n"
                "👤 Spieler\n"
                "🆔 Discord-ID\n"
                "📊 aktuelle Invites\n"
                "👥 erfolgreiche Beitritte\n"
                "🚪 verlassene Spieler\n"
                "🎁 bereits geclaimte Belohnungen\n"
                "🎫 noch verfügbare Belohnungen\n"
                "🔗 aktive Invite-Links\n\n"

                "Nutze **Spieler suchen**, um einen "
                "bestimmten Spieler aufzurufen."
            ),
            color=discord.Color.dark_grey(),
        )

        await channel.send(
            embed=embed,
            view=AdminSearchView(),
        )

        await interaction.response.send_message(
            "✅ Admin-Invite-Verwaltung wurde gepostet.",
            ephemeral=True,
        )

    # ========================================================
    # INVITE ERSTELLEN
    # ========================================================

    async def create_invite(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        channel = interaction.guild.get_channel(
            INVITE_PANEL_CHANNEL_ID
        )

        if channel is None:
            await interaction.followup.send(
                "❌ Invite-Kanal nicht gefunden.",
                ephemeral=True,
            )
            return

        try:
            invite = await channel.create_invite(
                max_age=172800,
                max_uses=0,
                unique=True,
                reason=(
                    f"Invite-System für "
                    f"{interaction.user}"
                ),
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Der Bot darf in diesem Kanal keine "
                "Invites erstellen.",
                ephemeral=True,
            )
            return

        except discord.HTTPException:
            logging.exception(
                "Invite konnte nicht erstellt werden."
            )

            await interaction.followup.send(
                "❌ Der Invite konnte nicht erstellt werden.",
                ephemeral=True,
            )
            return

        expires_at = utcnow() + timedelta(
            days=2
        )

        self.data["invites"][invite.code] = {
            "code": invite.code,
            "owner_id": interaction.user.id,
            "created_at": utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "uses": 0,
        }

        user_data = get_user_data(
            self.data,
            interaction.user.id,
        )

        user_data["username"] = str(
            interaction.user
        )

        user_data.setdefault(
            "created_invites",
            [],
        )

        user_data["created_invites"].append(
            invite.code
        )

        save_data(self.data)

        embed = discord.Embed(
            title="🔗 Dein persönlicher Invite",
            description=(
                f"Hier ist dein persönlicher "
                f"**NexoriaCraft Invite-Link**:\n\n"
                f"👉 **{invite.url}**\n\n"

                "⏳ **Gültig:** 2 Tage\n"
                "♾️ **Nutzungen:** unbegrenzt\n\n"

                "Teile den Link mit deinen Freunden. "
                "Erfolgreiche Beitritte werden deinem "
                "Invite-Konto gutgeschrieben."
            ),
            color=discord.Color.green(),
        )

        embed.add_field(
            name="📊 Deine aktuellen Invites",
            value=str(
                user_data.get(
                    "invites",
                    0,
                )
            ),
            inline=True,
        )

        embed.add_field(
            name="⏰ Ablauf",
            value=(
                f"<t:{int(expires_at.timestamp())}:R>"
            ),
            inline=True,
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )

        asyncio.create_task(
            self.expire_invite(
                invite.code
            )
        )

    # ========================================================
    # INVITE ABLAUF
    # ========================================================

    async def expire_invite(
        self,
        code,
    ):
        entry = self.data["invites"].get(
            code
        )

        if not entry:
            return

        try:
            expires_at = datetime.fromisoformat(
                entry["expires_at"]
            )
        except Exception:
            return

        delay = (
            expires_at - utcnow()
        ).total_seconds()

        if delay > 0:
            await asyncio.sleep(delay)

        entry = self.data["invites"].get(
            code
        )

        if not entry:
            return

        guild = None

        for current_guild in self.bot.guilds:
            guild = current_guild
            break

        if guild:
            try:
                invite = await guild.fetch_invite(
                    code
                )

                await invite.delete(
                    reason="Invite nach 2 Tagen abgelaufen"
                )

            except Exception:
                pass

        self.data["invites"].pop(
            code,
            None,
        )

        save_data(self.data)

    # ========================================================
    # INVITE CACHE
    # ========================================================

    async def refresh_invites(
        self,
        guild,
    ):
        try:
            invites = await guild.invites()
        except Exception:
            logging.exception(
                "Invites konnten nicht geladen werden."
            )
            return

        for invite in invites:
            self.invite_cache[
                invite.code
            ] = invite.uses or 0

    # ========================================================
    # MEMBER JOIN
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member,
    ):
        guild = member.guild

        try:
            before = dict(
                self.invite_cache
            )

            invites = await guild.invites()

        except Exception:
            logging.exception(
                "Invite-Erkennung fehlgeschlagen."
            )
            return

        used_invite = None

        for invite in invites:
            old_uses = before.get(
                invite.code,
                0,
            )

            new_uses = invite.uses or 0

            if new_uses > old_uses:
                used_invite = invite
                break

        for invite in invites:
            self.invite_cache[
                invite.code
            ] = invite.uses or 0

        if used_invite is None:
            return

        invite_data = self.data["invites"].get(
            used_invite.code
        )

        if not invite_data:
            return

        owner_id = int(
            invite_data["owner_id"]
        )

        # Self-invite verhindern
        if owner_id == member.id:
            return

        user_data = get_user_data(
            self.data,
            owner_id,
        )

        user_data["username"] = str(
            guild.get_member(owner_id)
            or owner_id
        )

        user_data["invites"] = (
            user_data.get(
                "invites",
                0,
            )
            + 1
        )

        user_data.setdefault(
            "joins",
            [],
        )

        user_data["joins"].append(
            {
                "user_id": member.id,
                "username": str(member),
                "date": utcnow().isoformat(),
                "invite": used_invite.code,
            }
        )

        invite_data["uses"] = (
            invite_data.get(
                "uses",
                0,
            )
            + 1
        )

        self.member_invites[
            member.id
        ] = owner_id

        save_data(self.data)

        logging.info(
            "%s hat %s eingeladen.",
            owner_id,
            member,
        )

    # ========================================================
    # MEMBER LEAVE
    # ========================================================

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member: discord.Member,
    ):
        owner_id = self.member_invites.pop(
            member.id,
            None,
        )

        if owner_id is None:
            return

        user_data = self.data["users"].get(
            str(owner_id)
        )

        if not user_data:
            return

        if user_data.get("invites", 0) > 0:
            user_data["invites"] -= 1

        user_data["left"] = (
            user_data.get(
                "left",
                0,
            )
            + 1
        )

        save_data(self.data)

    # ========================================================
    # STATS
    # ========================================================

    async def show_stats(
        self,
        interaction: discord.Interaction,
    ):
        user_data = get_user_data(
            self.data,
            interaction.user.id,
        )

        invites = user_data.get(
            "invites",
            0,
        )

        claimed = user_data.get(
            "claimed_rewards",
            [],
        )

        next_amount = next_reward(
            user_data
        )

        if next_amount:
            next_text = (
                f"{REWARDS[next_amount]['emoji']} "
                f"{next_amount} Invites"
            )
        else:
            next_text = "🏆 Alle Belohnungen erreicht"

        embed = discord.Embed(
            title="📊 Deine Invite-Statistik",
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="👥 Invites",
            value=str(invites),
            inline=True,
        )

        embed.add_field(
            name="🎁 Geclaimt",
            value=str(len(claimed)),
            inline=True,
        )

        embed.add_field(
            name="🎯 Nächste Belohnung",
            value=next_text,
            inline=False,
        )

        embed.add_field(
            name="🚪 Spieler verlassen",
            value=str(
                user_data.get(
                    "left",
                    0,
                )
            ),
            inline=True,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # ========================================================
    # REWARDS
    # ========================================================

    async def show_rewards(
        self,
        interaction: discord.Interaction,
    ):
        user_data = get_user_data(
            self.data,
            interaction.user.id,
        )

        invites = user_data.get(
            "invites",
            0,
        )

        claimed = user_data.get(
            "claimed_rewards",
            [],
        )

        embed = discord.Embed(
            title="🎁 Invite-Belohnungen",
            description=(
                "Sammle Invites und schalte "
                "immer bessere Belohnungen frei."
            ),
            color=discord.Color.gold(),
        )

        for amount, reward in REWARDS.items():
            if amount in claimed:
                status = "✅ GECLAIMT"
            elif invites >= amount:
                status = "🎫 VERFÜGBAR"
            else:
                status = (
                    f"🔒 Noch {amount - invites}"
                    f" Invites"
                )

            embed.add_field(
                name=(
                    f"{reward['emoji']} "
                    f"{reward['name']}"
                ),
                value=(
                    f"{reward['description']}\n"
                    f"**Status:** {status}"
                ),
                inline=False,
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # ========================================================
    # CLAIM MENU
    # ========================================================

    async def show_claim_menu(
        self,
        interaction: discord.Interaction,
    ):
        user_data = get_user_data(
            self.data,
            interaction.user.id,
        )

        available = [
            amount
            for amount in REWARDS
            if reward_available(
                user_data,
                amount,
            )
        ]

        if not available:
            await interaction.response.send_message(
                "❌ Du hast aktuell keine "
                "verfügbare Belohnung.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🎫 Belohnung claimen",
            description=(
                "Wähle unten die Belohnung aus, "
                "die du einlösen möchtest.\n\n"
                "Danach wird ein Claim-Ticket erstellt."
            ),
            color=discord.Color.green(),
        )

        await interaction.response.send_message(
            embed=embed,
            view=ClaimView(self),
            ephemeral=True,
        )

    # ========================================================
    # CLAIM TICKET
    # ========================================================

    async def create_claim_ticket(
        self,
        interaction: discord.Interaction,
        reward_amount: int,
        minecraft_name: str,
    ):
        guild = interaction.guild

        user_data = get_user_data(
            self.data,
            interaction.user.id,
        )

        if not reward_available(
            user_data,
            reward_amount,
        ):
            await interaction.response.send_message(
                "❌ Diese Belohnung ist nicht verfügbar.",
                ephemeral=True,
            )
            return

        existing = None

        for channel in guild.text_channels:
            topic = channel.topic or ""

            if (
                topic.startswith("invite-claim:")
                and f"user_id={interaction.user.id}" in topic
                and f"reward={reward_amount}" in topic
            ):
                existing = channel
                break

        if existing:
            await interaction.response.send_message(
                f"❌ Du hast bereits ein Claim-Ticket: "
                f"{existing.mention}",
                ephemeral=True,
            )
            return

        panel_channel = guild.get_channel(
            INVITE_PANEL_CHANNEL_ID
        )

        category = None

        if CLAIM_CATEGORY_ID:
            category = guild.get_channel(
                CLAIM_CATEGORY_ID
            )

        if category is None and panel_channel:
            category = panel_channel.category

        overwrites = {
            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                ),

            guild.me:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                ),
        }

        for member in guild.members:
            if member.guild_permissions.administrator:
                overwrites[member] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                    )
                )

        reward = REWARDS[reward_amount]

        channel = await guild.create_text_channel(
            name=(
                f"invite-claim-"
                f"{interaction.user.name.lower()}"
            )[:95],
            category=category,
            overwrites=overwrites,
            topic=(
                f"invite-claim:"
                f"user_id={interaction.user.id};"
                f"reward={reward_amount}"
            ),
            reason="Invite Reward Claim",
        )

        embed = discord.Embed(
            title="🎁 Invite-Belohnung",
            description=(
                f"👤 **Discord:** {interaction.user.mention}\n"
                f"🎮 **Minecraft:** `{minecraft_name}`\n\n"

                f"### {reward['emoji']} Belohnung\n"
                f"**{reward['name']}**\n\n"
                f"{reward['description']}\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                "Ein Administrator prüft jetzt deine "
                "Invite-Anzahl und gibt die Belohnung "
                "anschließend frei.\n\n"

                "⚠️ Bitte sende keine weiteren Nachrichten, "
                "bis das Team dein Claim bearbeitet hat."
            ),
            color=discord.Color.gold(),
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
        )

        await interaction.response.send_message(
            f"✅ Dein Claim-Ticket wurde erstellt: "
            f"{channel.mention}",
            ephemeral=True,
        )

    # ========================================================
    # ADMIN SUCHE
    # ========================================================

    async def search_player(
        self,
        interaction: discord.Interaction,
        query: str,
    ):
        query_lower = query.lower()

        found = []

        for user_id, user_data in self.data["users"].items():
            username = str(
                user_data.get(
                    "username",
                    "",
                )
            )

            if (
                query_lower in username.lower()
                or query == user_id
            ):
                found.append(
                    (
                        user_id,
                        user_data,
                    )
                )

        if not found:
            await interaction.response.send_message(
                "❌ Kein Spieler gefunden.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🔎 Invite-Spieler",
            color=discord.Color.blurple(),
        )

        for user_id, user_data in found[:10]:
            invites = user_data.get(
                "invites",
                0,
            )

            claimed = user_data.get(
                "claimed_rewards",
                [],
            )

            available = []

            for amount in REWARDS:
                if reward_available(
                    user_data,
                    amount,
                ):
                    available.append(
                        f"{amount} Invites"
                    )

            if available:
                available_text = ", ".join(
                    available
                )
            else:
                available_text = "Keine"

            embed.add_field(
                name=(
                    f"👤 "
                    f"{user_data.get('username', user_id)}"
                ),
                value=(
                    f"🆔 `{user_id}`\n"
                    f"📊 **Invites:** {invites}\n"
                    f"🎁 **Geclaimt:** "
                    f"{len(claimed)}\n"
                    f"🎫 **Verfügbar:** "
                    f"{available_text}\n"
                    f"🚪 **Leaver:** "
                    f"{user_data.get('left', 0)}"
                ),
                inline=False,
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # ========================================================
    # READY
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.refresh_invites(guild)

            for code, entry in list(
                self.data["invites"].items()
            ):
                try:
                    expires = datetime.fromisoformat(
                        entry["expires_at"]
                    )

                    if expires > utcnow():
                        asyncio.create_task(
                            self.expire_invite(
                                code
                            )
                        )

                except Exception:
                    pass

        save_data(self.data)

    # ========================================================
    # PERSISTENTE VIEWS
    # ========================================================

    async def cog_load(self):
        self.bot.add_view(
            InvitePanelView()
        )

        self.bot.add_view(
            AdminSearchView()
        )

    async def cog_unload(self):
        pass


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(
        Invites(bot)
    )
