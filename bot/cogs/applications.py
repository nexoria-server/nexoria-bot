from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from bot.services import (
    DEFAULT_APPLICATION_TYPES,
    ensure_guild_defaults,
    require_permission,
    safe_dm,
)


FORM_FIELDS = {
    "test_supporter": (
        ("Minecraft-Name, Discord-Name und Alter", "Grunddaten", True),
        ("Support-Erfahrung", "Erfahrung", True),
        ("Motivation für Nexoria Craft", "Motivation", True),
        ("Umgang mit Konflikten", "Konfliktlösung", True),
        ("Zeiten und Aktivität pro Woche", "Verfügbarkeit", True),
    ),
    "test_developer": (
        ("Minecraft-Name, Discord-Name und Alter", "Grunddaten", True),
        ("Programmiersprachen und Erfahrung", "Kenntnisse", True),
        ("GitHub, Portfolio oder Projektlinks", "Referenzen", True),
        ("Motivation für Nexoria Craft", "Motivation", True),
        ("Zeiten und Aktivität pro Woche", "Verfügbarkeit", True),
    ),
    "developer": (
        ("Minecraft-Name, Discord-Name und Alter", "Grunddaten", True),
        ("Programmiersprachen und Erfahrung", "Kenntnisse", True),
        ("GitHub, Portfolio oder Projektlinks", "Referenzen", True),
        ("Motivation für Nexoria Craft", "Motivation", True),
        ("Zeiten und Aktivität pro Woche", "Verfügbarkeit", True),
    ),
    "builder": (
        ("Minecraft-Name, Discord-Name und Alter", "Grunddaten", True),
        ("Baustile und bisherige Erfahrung", "Erfahrung", True),
        ("WorldEdit und weitere Werkzeuge", "Werkzeuge", True),
        ("Portfolio oder Bilder deiner Builds", "Referenzen", True),
        ("Motivation und Verfügbarkeit", "Motivation", True),
    ),
    "media": (
        ("Minecraft-Name, Discord-Name und Alter", "Grunddaten", True),
        ("Plattform und Kanal-/Profil-Link", "Profil", True),
        ("Follower und durchschnittliche Videoaufrufe", "Reichweite", True),
        ("Aufrufe/Links der letzten Videos", "Letzte Inhalte", True),
        ("Nexoria-Craft-Content und Motivation", "Nexoria Craft", True),
    ),
    "partner": (
        ("Server-/Projektname und Ansprechpartner", "Grunddaten", True),
        ("Discord-Link, Serveradresse und Website", "Links", True),
        ("Mitglieder und durchschnittlich Aktive", "Community", True),
        ("Kurze Projektbeschreibung", "Projekt", True),
        ("Gewünschte Zusammenarbeit und Nutzen", "Partnerschaft", True),
    ),
}


def _application_id(message: discord.Message | None) -> int | None:
    if not message or not message.embeds or not message.embeds[0].footer.text:
        return None
    match = re.fullmatch(r"application:(\d+)", message.embeds[0].footer.text)
    return int(match.group(1)) if match else None


class ApplicationModal(discord.ui.Modal):
    def __init__(self, type_key: str, type_name: str) -> None:
        super().__init__(title=f"Bewerbung: {type_name}"[:45], timeout=900)
        self.type_key = type_key
        for label, placeholder, required in FORM_FIELDS[type_key]:
            self.add_item(
                discord.ui.TextInput(
                    label=label[:45],
                    placeholder=placeholder,
                    style=discord.TextStyle.paragraph,
                    min_length=2,
                    max_length=900,
                    required=required,
                )
            )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        database = interaction.client.db
        existing = await database.fetchone(
            "SELECT id FROM applications WHERE guild_id=? AND user_id=? "
            "AND type_key=? AND status='open'",
            (interaction.guild.id, interaction.user.id, self.type_key),
        )
        if existing:
            await interaction.response.send_message(
                f"Du hast bereits eine offene Bewerbung (#{existing['id']}).", ephemeral=True
            )
            return
        answers = {
            item.label: str(item.value).strip()
            for item in self.children
            if isinstance(item, discord.ui.TextInput)
        }
        try:
            cursor = await database.execute(
                "INSERT INTO applications(guild_id,user_id,type_key,answers) VALUES(?,?,?,?)",
                (
                    interaction.guild.id,
                    interaction.user.id,
                    self.type_key,
                    json.dumps(answers, ensure_ascii=False),
                ),
            )
        except aiosqlite.IntegrityError:
            await interaction.response.send_message(
                "Eine Bewerbung dieser Art wurde gleichzeitig bereits gespeichert.",
                ephemeral=True,
            )
            return
        application_id = int(cursor.lastrowid)
        type_row = await database.fetchone(
            "SELECT name FROM application_types WHERE guild_id=? AND type_key=?",
            (interaction.guild.id, self.type_key),
        )
        embed = discord.Embed(
            title=f"Neue {type_row['name']}-Bewerbung #{application_id}",
            description=f"Bewerber: {interaction.user.mention} (`{interaction.user.id}`)",
            color=discord.Color.blurple(),
            timestamp=datetime.now(UTC),
        )
        for question, answer in answers.items():
            embed.add_field(name=question, value=answer[:1024], inline=False)
        embed.set_footer(text=f"application:{application_id}")
        review_id = await database.setting(interaction.guild.id, "channel.application_review", 0)
        if not review_id:
            legacy = await database.guild_config(interaction.guild.id)
            review_id = legacy["application_channel_id"]
        review_channel = interaction.guild.get_channel(int(review_id or 0))
        if isinstance(review_channel, discord.TextChannel):
            await review_channel.send(embed=embed, view=ApplicationDecisionView())
            result = f"✅ Bewerbung #{application_id} wurde eingereicht."
        else:
            result = (
                f"✅ Bewerbung #{application_id} wurde gespeichert. Ein Admin muss noch "
                "den Prüfkanal unter /settings → Kanäle festlegen."
            )
        await interaction.response.send_message(result, ephemeral=True)


class ApplicationTypeSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Bewerbungsart auswählen",
            custom_id="nexoria:application:type",
            options=[
                discord.SelectOption(label=value["name"], value=key)
                for key, value in DEFAULT_APPLICATION_TYPES.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        await ensure_guild_defaults(interaction.client.db, interaction.guild.id)
        row = await interaction.client.db.fetchone(
            "SELECT name,enabled FROM application_types WHERE guild_id=? AND type_key=?",
            (interaction.guild.id, self.values[0]),
        )
        if not row or not row["enabled"]:
            await interaction.response.send_message(
                "Diese Bewerbungsart ist derzeit geschlossen.", ephemeral=True
            )
            return
        await interaction.response.send_modal(ApplicationModal(self.values[0], row["name"]))


class ApplicationPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(ApplicationTypeSelect())


class DecisionReasonModal(discord.ui.Modal):
    reason = discord.ui.TextInput(
        label="Begründung für den Bewerber",
        style=discord.TextStyle.paragraph,
        min_length=3,
        max_length=1000,
    )

    def __init__(self, application_id: int, decision: str) -> None:
        title = "Bewerbung annehmen" if decision == "accepted" else "Bewerbung ablehnen"
        super().__init__(title=title)
        self.application_id = application_id
        self.decision = decision

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        database = interaction.client.db
        if not await require_permission(interaction, database, "applications"):
            return
        row = await database.fetchone(
            "SELECT a.*,t.name,t.test_days FROM applications a JOIN application_types t "
            "ON t.guild_id=a.guild_id AND t.type_key=a.type_key "
            "WHERE a.id=? AND a.guild_id=?",
            (self.application_id, interaction.guild.id),
        )
        if not row or row["status"] != "open":
            await interaction.response.send_message(
                "Diese Bewerbung wurde bereits bearbeitet.", ephemeral=True
            )
            return
        now = datetime.now(UTC)
        test_end = now + timedelta(days=int(row["test_days"]))
        cursor = await database.execute(
            "UPDATE applications SET status=?,reviewer_id=?,decision_reason=?,decided_at=?,"
            "test_start=?,test_end=? WHERE id=? AND status='open'",
            (
                self.decision,
                interaction.user.id,
                str(self.reason),
                now.isoformat(),
                now.isoformat() if self.decision == "accepted" else None,
                test_end.isoformat() if self.decision == "accepted" else None,
                self.application_id,
            ),
        )
        if cursor.rowcount != 1:
            await interaction.response.send_message(
                "Diese Bewerbung wurde gleichzeitig bereits bearbeitet.", ephemeral=True
            )
            return
        member = interaction.guild.get_member(row["user_id"])
        role_note = ""
        if member and self.decision == "accepted":
            role_ids = await database.roles(
                interaction.guild.id, f"application.{row['type_key']}.test"
            )
            role_ids |= await database.roles(
                interaction.guild.id, f"application.{row['type_key']}.accepted"
            )
            roles = [role for role_id in role_ids if (role := interaction.guild.get_role(role_id))]
            if roles:
                try:
                    await member.add_roles(*roles, reason=f"Bewerbung #{self.application_id}")
                except discord.Forbidden:
                    role_note = (
                        " Rollen konnten wegen der Discord-Rollenreihenfolge nicht vergeben werden."
                    )
        if self.decision == "accepted":
            description = (
                f"Deine Bewerbung als **{row['name']}** wurde angenommen.\n\n"
                f"**Begründung:** {self.reason}\n"
                f"**Test-/Kennenlernphase:** {row['test_days']} Tage, bis "
                f"<t:{int(test_end.timestamp())}:D>.\n\n"
                "Willkommen! Das Team meldet sich mit den nächsten Schritten bei dir."
            )
            color = discord.Color.green()
            title = f"✅ {row['name']}-Bewerbung angenommen"
        else:
            description = (
                f"Deine Bewerbung als **{row['name']}** wurde abgelehnt.\n\n"
                f"**Begründung:** {self.reason}\n\n"
                "Danke für dein Interesse an Nexoria Craft. Eine spätere neue Bewerbung ist möglich."
            )
            color = discord.Color.red()
            title = f"❌ {row['name']}-Bewerbung abgelehnt"
        dm_sent = bool(
            member
            and await safe_dm(
                member, discord.Embed(title=title, description=description, color=color)
            )
        )
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            embed.color = color
            embed.add_field(
                name="Entscheidung",
                value=f"{title}\nVon {interaction.user.mention}\n{self.reason}",
                inline=False,
            )
            await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(
            f"✅ Entscheidung gespeichert. DM: {'gesendet' if dm_sent else 'nicht zustellbar'}.{role_note}",
            ephemeral=True,
        )


class ApplicationDecisionView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    async def open_modal(self, interaction: discord.Interaction, decision: str) -> None:
        if not await require_permission(interaction, interaction.client.db, "applications"):
            return
        application_id = _application_id(interaction.message)
        if application_id is None:
            await interaction.response.send_message("Bewerbungs-ID fehlt.", ephemeral=True)
            return
        await interaction.response.send_modal(DecisionReasonModal(application_id, decision))

    @discord.ui.button(
        label="Annehmen", style=discord.ButtonStyle.success, custom_id="nexoria:application:accept"
    )
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "accepted")

    @discord.ui.button(
        label="Ablehnen", style=discord.ButtonStyle.danger, custom_id="nexoria:application:deny"
    )
    async def deny(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "denied")


class ApplicationArchiveTypeSelect(discord.ui.Select):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(
            placeholder="Bewerbungsart auswählen",
            options=[
                discord.SelectOption(label="Alle", value="all"),
                *[
                    discord.SelectOption(label=value["name"], value=key)
                    for key, value in DEFAULT_APPLICATION_TYPES.items()
                ],
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not await require_permission(
            interaction, interaction.client.db, "application_archive"
        ):
            return
        params: list[object] = [interaction.guild.id, self.user_id]
        query = (
            "SELECT a.*,t.name FROM applications a JOIN application_types t "
            "ON t.guild_id=a.guild_id AND t.type_key=a.type_key "
            "WHERE a.guild_id=? AND a.user_id=?"
        )
        if self.values[0] != "all":
            query += " AND a.type_key=?"
            params.append(self.values[0])
        rows = await interaction.client.db.fetchall(
            query + " ORDER BY a.id DESC LIMIT 10", tuple(params)
        )
        if not rows:
            await interaction.response.send_message("Keine Bewerbungen gefunden.", ephemeral=True)
            return
        embeds = []
        for row in rows:
            answers = json.loads(row["answers"])
            embed = discord.Embed(
                title=f"#{row['id']} · {row['name']} · {row['status']}",
                description="\n".join(f"**{key}:** {value}" for key, value in answers.items())[
                    :4000
                ],
                color=discord.Color.blurple(),
            )
            if row["decision_reason"]:
                embed.add_field(name="Entscheidung", value=row["decision_reason"][:1024])
            embeds.append(embed)
        await interaction.response.send_message(embeds=embeds, ephemeral=True)


class ApplicationArchiveTypeView(discord.ui.View):
    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=300)
        self.add_item(ApplicationArchiveTypeSelect(user_id))


class ApplicationArchiveUserSelect(discord.ui.UserSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Spieler auswählen",
            min_values=1,
            max_values=1,
            custom_id="nexoria:application:archive:user",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await require_permission(interaction, interaction.client.db, "application_archive"):
            return
        await interaction.response.send_message(
            "Bewerbungsart auswählen:",
            view=ApplicationArchiveTypeView(self.values[0].id),
            ephemeral=True,
        )


class ApplicationArchiveView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(ApplicationArchiveUserSelect())


class Applications(commands.GroupCog, group_name="application", group_description="Bewerbungen"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(ApplicationPanelView())
        self.bot.add_view(ApplicationDecisionView())
        self.bot.add_view(ApplicationArchiveView())

    @app_commands.command(name="panel", description="Postet das Bewerbungs-Panel im Zielkanal.")
    @app_commands.default_permissions(manage_guild=True)
    async def panel(self, interaction: discord.Interaction, kanal: discord.TextChannel) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "applications"
        ):
            return
        await ensure_guild_defaults(self.bot.db, interaction.guild.id)
        embed = discord.Embed(
            title="📝 Nexoria Craft – Bewerbungen",
            description=(
                "Wähle die passende Bewerbungsart aus. Deine Angaben werden sicher "
                "gespeichert und nur dem zuständigen Team angezeigt."
            ),
            color=discord.Color.blurple(),
        )
        await kanal.send(embed=embed, view=ApplicationPanelView())
        await interaction.response.send_message(
            f"✅ Panel in {kanal.mention} erstellt.", ephemeral=True
        )

    @app_commands.command(name="archive", description="Postet die Suche im Bewerbungsarchiv.")
    @app_commands.default_permissions(manage_guild=True)
    async def archive(self, interaction: discord.Interaction, kanal: discord.TextChannel) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "application_archive"
        ):
            return
        embed = discord.Embed(
            title="🗃️ Bewerbungsarchiv",
            description="Wähle einen Spieler und danach die Bewerbungsart aus.",
            color=discord.Color.blurple(),
        )
        await kanal.send(embed=embed, view=ApplicationArchiveView())
        await interaction.response.send_message(
            f"✅ Archiv in {kanal.mention} erstellt.", ephemeral=True
        )

    @app_commands.command(name="duration", description="Setzt die Testdauer einer Bewerbungsart.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.choices(
        typ=[
            app_commands.Choice(name=value["name"], value=key)
            for key, value in DEFAULT_APPLICATION_TYPES.items()
        ]
    )
    async def duration(
        self,
        interaction: discord.Interaction,
        typ: app_commands.Choice[str],
        tage: app_commands.Range[int, 1, 365],
    ) -> None:
        if not interaction.guild or not await require_permission(
            interaction, self.bot.db, "settings"
        ):
            return
        await ensure_guild_defaults(self.bot.db, interaction.guild.id)
        await self.bot.db.execute(
            "UPDATE application_types SET test_days=? WHERE guild_id=? AND type_key=?",
            (tage, interaction.guild.id, typ.value),
        )
        await interaction.response.send_message(
            f"✅ Testdauer für **{typ.name}**: {tage} Tage.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Applications(bot))
