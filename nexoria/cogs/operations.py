from __future__ import annotations

import asyncio
import io
import random
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks
from mcstatus import JavaServer

from nexoria.checks import require, safe_dm
from nexoria.database import Database
from nexoria.domain import APPLICATION_DEFAULT_DAYS


def utcnow() -> datetime:
    return datetime.now(UTC)


class TicketTypeSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(label=name, value=name.lower())
            for name in ("Support", "Bewerbung", "Media", "Partner", "Team", "Giveaway")
        ]
        super().__init__(
            placeholder="Ticketart auswählen",
            options=options,
            custom_id="nexoria:ticket:type",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        db: Database = interaction.client.database  # type: ignore[attr-defined]
        existing = await db.rows(
            "SELECT channel_id FROM tickets WHERE guild_id=? AND owner_id=? "
            "AND type=? AND status='open'",
            (interaction.guild.id, interaction.user.id, self.values[0]),
        )
        if existing:
            await interaction.response.send_message(
                f"Du hast bereits ein offenes Ticket: <#{existing[0]['channel_id']}>",
                ephemeral=True,
            )
            return
        category_id = await db.get(interaction.guild.id, f"ticket.category.{self.values[0]}")
        category = interaction.guild.get_channel(category_id) if category_id else None
        staff_ids = await db.roles(interaction.guild.id, "ticket.staff")
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True
            ),
        }
        for role_id in staff_ids:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
        await interaction.response.defer(ephemeral=True)
        channel = await interaction.guild.create_text_channel(
            name=f"{self.values[0]}-{interaction.user.name}"[:100],
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=overwrites,
            reason=f"Ticket von {interaction.user}",
        )
        ticket_id = await db.execute(
            "INSERT INTO tickets(guild_id,channel_id,owner_id,type,created_at) "
            "VALUES(?,?,?,?,datetime('now'))",
            (interaction.guild.id, channel.id, interaction.user.id, self.values[0]),
        )
        await channel.send(
            interaction.user.mention,
            embed=discord.Embed(
                title=f"🎫 Ticket #{ticket_id}",
                description="Beschreibe dein Anliegen möglichst genau.",
            ),
            view=CloseTicketView(),
        )
        await interaction.followup.send(f"Ticket erstellt: {channel.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())


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
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            return
        db: Database = interaction.client.database  # type: ignore[attr-defined]
        rows = await db.rows(
            "SELECT id,owner_id FROM tickets WHERE channel_id=? AND status='open'",
            (interaction.channel.id,),
        )
        if not rows:
            await interaction.response.send_message(
                "Dieses Ticket ist bereits geschlossen.", ephemeral=True
            )
            return
        staff = await db.roles(interaction.guild.id, "ticket.staff")
        user_roles = {role.id for role in getattr(interaction.user, "roles", [])}
        if interaction.user.id != rows[0]["owner_id"] and not (
            staff & user_roles or interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "Du darfst dieses Ticket nicht schließen.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        chunks = []
        async for message in interaction.channel.history(limit=1000, oldest_first=True):
            chunks.append(
                f"[{message.created_at.isoformat()}] {message.author}: {message.clean_content}"
            )
        transcript = "\n".join(chunks)
        await db.execute(
            "UPDATE tickets SET status='closed',closed_at=datetime('now'),closed_by=?,transcript=? "
            "WHERE channel_id=?",
            (interaction.user.id, transcript, interaction.channel.id),
        )
        archive_id = await db.get(interaction.guild.id, "channel.ticket_archive")
        archive = interaction.guild.get_channel(archive_id) if archive_id else None
        if isinstance(archive, discord.TextChannel):
            file = discord.File(
                io.BytesIO(transcript.encode()), filename=f"ticket-{rows[0]['id']}.txt"
            )
            await archive.send(
                f"Ticket #{rows[0]['id']} • geschlossen von {interaction.user.mention}", file=file
            )
        await interaction.followup.send("Ticket archiviert; Kanal wird gelöscht.", ephemeral=True)
        await interaction.channel.delete(reason=f"Ticket geschlossen von {interaction.user}")


class ApplyModal(discord.ui.Modal):
    answers = discord.ui.TextInput(
        label="Deine Bewerbung",
        style=discord.TextStyle.paragraph,
        placeholder="Stelle dich vor, nenne Erfahrung, Motivation und relevante Links.",
        min_length=50,
        max_length=4000,
    )

    def __init__(self, application_type: str) -> None:
        super().__init__(title=f"Bewerbung: {application_type}"[:45])
        self.application_type = application_type

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        db: Database = interaction.client.database  # type: ignore[attr-defined]
        open_rows = await db.rows(
            "SELECT id FROM applications WHERE guild_id=? AND user_id=? "
            "AND type=? AND status='open'",
            (interaction.guild.id, interaction.user.id, self.application_type),
        )
        if open_rows:
            await interaction.response.send_message(
                "Dafür existiert bereits eine offene Bewerbung.", ephemeral=True
            )
            return
        application_id = await db.execute(
            "INSERT INTO applications(guild_id,user_id,type,answers,created_at) "
            "VALUES(?,?,?,?,datetime('now'))",
            (interaction.guild.id, interaction.user.id, self.application_type, str(self.answers)),
        )
        review_id = await db.get(interaction.guild.id, "channel.application_review")
        review = interaction.guild.get_channel(review_id) if review_id else None
        if isinstance(review, discord.TextChannel):
            embed = discord.Embed(
                title=f"📝 Bewerbung #{application_id} – {self.application_type}",
                description=str(self.answers)[:4000],
                color=discord.Color.blurple(),
            )
            embed.set_author(
                name=str(interaction.user), icon_url=interaction.user.display_avatar.url
            )
            await review.send(embed=embed)
        await interaction.response.send_message(
            f"Deine {self.application_type}-Bewerbung wurde als #{application_id} gespeichert.",
            ephemeral=True,
        )


class ApplicationSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(label=name, value=name)
            for name in ("Test Supporter", "Test Developer", "Media", "Partner")
        ]
        super().__init__(
            placeholder="Bewerbungsart auswählen",
            options=options,
            custom_id="nexoria:application:type",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ApplyModal(self.values[0]))


class ApplicationPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(ApplicationSelect())


class AnnouncementConfirm(discord.ui.View):
    def __init__(
        self,
        author_id: int,
        channel: discord.TextChannel,
        embed: discord.Embed,
        mention: str | None,
    ) -> None:
        super().__init__(timeout=180)
        self.author_id = author_id
        self.channel = channel
        self.embed = embed
        self.mention = mention

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="Senden", emoji="✅", style=discord.ButtonStyle.success)
    async def send(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        allowed_mentions = discord.AllowedMentions(
            everyone=self.mention in ("@everyone", "@here"), roles=True, users=False
        )
        await self.channel.send(
            content=self.mention, embed=self.embed, allowed_mentions=allowed_mentions
        )
        await interaction.response.edit_message(
            content="Announcement gesendet.", embed=None, view=None
        )

    @discord.ui.button(label="Abbrechen", emoji="✖️", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Abgebrochen.", embed=None, view=None)


class GiveawayEntryView(discord.ui.View):
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
        db: Database = interaction.client.database  # type: ignore[attr-defined]
        rows = await db.rows(
            "SELECT id,status FROM giveaways WHERE guild_id=? AND message_id=?",
            (interaction.guild.id, interaction.message.id),
        )
        if not rows or rows[0]["status"] != "open":
            await interaction.response.send_message("Dieses Giveaway ist beendet.", ephemeral=True)
            return
        await db.execute(
            "INSERT OR IGNORE INTO giveaway_entries(giveaway_id,user_id) VALUES(?,?)",
            (rows[0]["id"], interaction.user.id),
        )
        await interaction.response.send_message("Teilnahme gespeichert.", ephemeral=True)


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
        db: Database = interaction.client.database  # type: ignore[attr-defined]
        rows = await db.rows(
            "SELECT g.id,g.prize FROM giveaways g "
            "LEFT JOIN giveaway_claims c ON c.giveaway_id=g.id AND c.user_id=? "
            "WHERE g.guild_id=? AND g.winner_id=? AND g.status='closed' "
            "AND c.giveaway_id IS NULL ORDER BY g.id DESC LIMIT 1",
            (interaction.user.id, interaction.guild.id, interaction.user.id),
        )
        if not rows:
            await interaction.response.send_message(
                "Du hast keinen offenen Gewinn oder bereits ein Ticket erstellt.", ephemeral=True
            )
            return
        category_id = await db.get(interaction.guild.id, "ticket.category.giveaway")
        category = interaction.guild.get_channel(category_id) if category_id else None
        staff_ids = await db.roles(interaction.guild.id, "ticket.staff")
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True
            ),
        }
        for role_id in staff_ids:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
        await interaction.response.defer(ephemeral=True)
        channel = await interaction.guild.create_text_channel(
            name=f"gewinn-{interaction.user.name}"[:100],
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=overwrites,
            reason=f"Giveaway-Gewinn #{rows[0]['id']}",
        )
        ticket_id = await db.execute(
            "INSERT INTO tickets(guild_id,channel_id,owner_id,type,created_at) "
            "VALUES(?,?,?,?,datetime('now'))",
            (interaction.guild.id, channel.id, interaction.user.id, "giveaway"),
        )
        await db.execute(
            "INSERT INTO giveaway_claims(giveaway_id,user_id,ticket_id) VALUES(?,?,?)",
            (rows[0]["id"], interaction.user.id, ticket_id),
        )
        await channel.send(
            interaction.user.mention,
            embed=discord.Embed(
                title=f"🎁 Gewinn: {rows[0]['prize']}",
                description="Das Team meldet sich hier bei dir.",
            ),
            view=CloseTicketView(),
        )
        await interaction.followup.send(
            f"Gewinn-Ticket erstellt: {channel.mention}", ephemeral=True
        )


class Operations(commands.Cog):
    ticket = app_commands.Group(name="ticket", description="Ticket-System")
    application = app_commands.Group(name="application", description="Bewerbungssystem")
    minecraft = app_commands.Group(name="minecraft", description="Minecraft-Status")
    giveaway = app_commands.Group(name="giveaway", description="Giveaways")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._minecraft_locks: dict[int, asyncio.Lock] = {}
        self.background.start()
        bot.add_view(TicketPanelView())
        bot.add_view(CloseTicketView())
        bot.add_view(ApplicationPanelView())
        bot.add_view(GiveawayEntryView())
        bot.add_view(GiveawayClaimView())

    def cog_unload(self) -> None:
        self.background.cancel()

    @property
    def db(self) -> Database:
        return self.bot.database  # type: ignore[attr-defined]

    @ticket.command(name="panel", description="Postet das Ticket-Panel im gewünschten Kanal.")
    async def ticket_panel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        if not interaction.guild or not await require(interaction, self.db, "tickets"):
            return
        await channel.send(
            embed=discord.Embed(
                title="🎫 Nexoria Tickets", description="Wähle die passende Ticketart aus."
            ),
            view=TicketPanelView(),
        )
        await interaction.response.send_message(
            f"Panel in {channel.mention} erstellt.", ephemeral=True
        )

    @ticket.command(name="category", description="Legt die Kategorie für eine Ticketart fest.")
    async def ticket_category(
        self, interaction: discord.Interaction, ticket_type: str, category: discord.CategoryChannel
    ) -> None:
        if not interaction.guild or not await require(interaction, self.db, "tickets"):
            return
        await self.db.set(
            interaction.guild.id, f"ticket.category.{ticket_type.lower()}", category.id
        )
        await interaction.response.send_message("Ticket-Kategorie gespeichert.", ephemeral=True)

    @application.command(name="panel", description="Postet das Bewerbungs-Panel.")
    async def application_panel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        if not interaction.guild or not await require(interaction, self.db, "applications"):
            return
        await channel.send(
            embed=discord.Embed(
                title="📝 Bewerbungen",
                description="Wähle eine Bewerbungsart und fülle das Formular aus.",
            ),
            view=ApplicationPanelView(),
        )
        await interaction.response.send_message(
            f"Panel in {channel.mention} erstellt.", ephemeral=True
        )

    @application.command(name="decide", description="Nimmt eine Bewerbung an oder lehnt sie ab.")
    @app_commands.choices(
        decision=[
            app_commands.Choice(name="Annehmen", value="accepted"),
            app_commands.Choice(name="Ablehnen", value="denied"),
        ]
    )
    async def application_decide(
        self,
        interaction: discord.Interaction,
        application_id: int,
        decision: app_commands.Choice[str],
        reason: str = "Keine Angabe",
    ) -> None:
        if not interaction.guild or not await require(interaction, self.db, "applications"):
            return
        rows = await self.db.rows(
            "SELECT * FROM applications WHERE id=? AND guild_id=? AND status='open'",
            (application_id, interaction.guild.id),
        )
        if not rows:
            await interaction.response.send_message(
                "Offene Bewerbung nicht gefunden.", ephemeral=True
            )
            return
        row = rows[0]
        user = interaction.guild.get_member(row["user_id"])
        days = int(
            await self.db.get(
                interaction.guild.id,
                f"application.days.{row['type']}",
                APPLICATION_DEFAULT_DAYS.get(row["type"], 14),
            )
        )
        start, end = utcnow(), utcnow() + timedelta(days=days)
        await self.db.execute(
            "UPDATE applications SET status=?,reviewer_id=?,reason=?,decided_at=datetime('now'),"
            "test_start=?,test_end=? WHERE id=?",
            (
                decision.value,
                interaction.user.id,
                reason,
                start.isoformat(),
                end.isoformat(),
                application_id,
            ),
        )
        if user and decision.value == "accepted":
            role_ids = await self.db.roles(
                interaction.guild.id, f"application.{row['type']}.accepted"
            )
            valid_roles = [interaction.guild.get_role(role_id) for role_id in role_ids]
            await user.add_roles(
                *[role for role in valid_roles if role], reason=f"Bewerbung #{application_id}"
            )
        if user:
            embed = discord.Embed(
                title=f"Bewerbung {decision.name}",
                description=(
                    f"Deine Bewerbung als **{row['type']}** wurde "
                    f"{decision.name.lower()}.\nGrund: {reason}"
                ),
                color=discord.Color.green()
                if decision.value == "accepted"
                else discord.Color.red(),
            )
            if row["type"] == "Test Supporter" and decision.value == "accepted":
                mentor_roles = await self.db.roles(interaction.guild.id, "leadership.Mentoren")
                mentors = [
                    member.mention
                    for member in interaction.guild.members
                    if mentor_roles & {role.id for role in member.roles}
                ]
                mentor = mentors[0] if mentors else "noch nicht zugewiesen"
                template = await self.db.get(
                    interaction.guild.id,
                    "application.onboarding.Test Supporter",
                    "Willkommen im Team, {user}! Unterstütze Spieler respektvoll, "
                    "dokumentiere Tickets "
                    "und frage bei Unsicherheit deinen Mentor {mentor}. Deine Testphase dauert "
                    "{test_duration} Tage und endet am {end_date}.",
                )
                embed.add_field(
                    name="🎓 Test-Supporter-Onboarding",
                    value=template.format(
                        user=user.mention,
                        username=user.name,
                        role="Test Supporter",
                        application=row["type"],
                        test_duration=days,
                        start_date=start.date(),
                        end_date=end.date(),
                        server=interaction.guild.name,
                        mentor=mentor,
                    )[:1024],
                    inline=False,
                )
                await self.db.execute(
                    "UPDATE applications SET onboarding_sent_at=datetime('now') WHERE id=? "
                    "AND onboarding_sent_at IS NULL",
                    (application_id,),
                )
            await safe_dm(user, embed=embed)
        await interaction.response.send_message("Entscheidung gespeichert.", ephemeral=True)

    @app_commands.command(
        name="announce", description="Zeigt eine Vorschau und sendet ein Announcement."
    )
    @app_commands.choices(
        ping=[
            app_commands.Choice(name="Kein Ping", value="none"),
            app_commands.Choice(name="@everyone", value="@everyone"),
            app_commands.Choice(name="@here", value="@here"),
        ]
    )
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        message: str,
        ping: app_commands.Choice[str],
        role: discord.Role | None = None,
    ) -> None:
        if not interaction.guild or not await require(interaction, self.db, "announcements"):
            return
        mention = role.mention if role else (None if ping.value == "none" else ping.value)
        embed = discord.Embed(
            title=title[:256], description=message[:4000], color=discord.Color.blurple()
        )
        await interaction.response.send_message(
            content=f"Vorschau für {channel.mention}\nPing: {mention or 'Kein Ping'}",
            embed=embed,
            view=AnnouncementConfirm(interaction.user.id, channel, embed, mention),
            ephemeral=True,
        )

    @minecraft.command(name="configure", description="Konfiguriert Adresse und Panel-Kanal.")
    async def minecraft_configure(
        self, interaction: discord.Interaction, address: str, channel: discord.TextChannel
    ) -> None:
        if not interaction.guild or not await require(interaction, self.db, "minecraft"):
            return
        await self.db.set(interaction.guild.id, "minecraft.address", address)
        await self.db.set(interaction.guild.id, "minecraft.channel", channel.id)
        await interaction.response.send_message("Minecraft-Panel konfiguriert.", ephemeral=True)

    @giveaway.command(name="start", description="Startet ein persistentes Giveaway.")
    async def giveaway_start(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        prize: str,
        minutes: app_commands.Range[int, 1, 10080],
    ) -> None:
        if not interaction.guild or not await require(interaction, self.db, "giveaways"):
            return
        end = utcnow() + timedelta(minutes=minutes)
        embed = discord.Embed(
            title="🎁 Giveaway",
            description=f"Gewinn: **{prize}**\nEnde: <t:{int(end.timestamp())}:R>",
            color=discord.Color.gold(),
        )
        message = await channel.send(embed=embed, view=GiveawayEntryView())
        await self.db.execute(
            "INSERT INTO giveaways(guild_id,channel_id,message_id,prize,ends_at) VALUES(?,?,?,?,?)",
            (interaction.guild.id, channel.id, message.id, prize, end.isoformat()),
        )
        await interaction.response.send_message("Giveaway gestartet.", ephemeral=True)

    async def update_minecraft(self, guild: discord.Guild) -> None:
        address = await self.db.get(guild.id, "minecraft.address")
        channel_id = await self.db.get(guild.id, "minecraft.channel")
        channel = guild.get_channel(channel_id) if channel_id else None
        if not address or not isinstance(channel, discord.TextChannel):
            return
        lock = self._minecraft_locks.setdefault(guild.id, asyncio.Lock())
        if lock.locked():
            return
        async with lock:
            try:
                status = await JavaServer.lookup(address).async_status()
                players = status.players.sample or []
                names = [getattr(player, "name", str(player)) for player in players]
                description = (
                    f"🟢 Online • {status.latency:.0f} ms\n"
                    f"Spieler: **{status.players.online}/{status.players.max}**\n"
                    + ("\n".join(f"• {name}" for name in names[:20]) if names else "")
                )
            except Exception:
                description = "🔴 Server nicht erreichbar"
            embed = discord.Embed(title="⛏️ Minecraft Status", description=description)
            rows = await self.db.rows(
                "SELECT message_id,payload_hash FROM panels WHERE guild_id=? AND kind='minecraft'",
                (guild.id,),
            )
            digest = str(hash(description))
            if rows and rows[0]["payload_hash"] == digest:
                return
            message = None
            if rows and rows[0]["message_id"]:
                try:
                    message = await channel.fetch_message(rows[0]["message_id"])
                except (discord.NotFound, discord.Forbidden):
                    pass
            message = (
                await message.edit(embed=embed) if message else await channel.send(embed=embed)
            )
            await self.db.execute(
                "INSERT INTO panels(guild_id,kind,channel_id,message_id,payload_hash) "
                "VALUES(?,?,?,?,?) "
                "ON CONFLICT(guild_id,kind) DO UPDATE SET channel_id=excluded.channel_id,"
                "message_id=excluded.message_id,payload_hash=excluded.payload_hash",
                (guild.id, "minecraft", channel.id, message.id, digest),
            )

    async def finish_giveaways(self) -> None:
        rows = await self.db.rows(
            "SELECT * FROM giveaways WHERE status='open' AND ends_at<=?", (utcnow().isoformat(),)
        )
        for row in rows:
            entries = await self.db.rows(
                "SELECT user_id FROM giveaway_entries WHERE giveaway_id=?", (row["id"],)
            )
            winner_id = random.choice(entries)["user_id"] if entries else None
            await self.db.execute(
                "UPDATE giveaways SET status='closed',winner_id=? WHERE id=?",
                (winner_id, row["id"]),
            )
            guild = self.bot.get_guild(row["guild_id"])
            channel = guild.get_channel(row["channel_id"]) if guild else None
            if isinstance(channel, discord.TextChannel):
                text = (
                    f"🎉 <@{winner_id}> gewinnt **{row['prize']}**!"
                    if winner_id
                    else "Keine Teilnahme."
                )
                await channel.send(
                    text,
                    view=GiveawayClaimView() if winner_id else None,
                    allowed_mentions=discord.AllowedMentions(users=True),
                )

    @tasks.loop(seconds=15)
    async def background(self) -> None:
        await self.finish_giveaways()
        await asyncio.gather(*(self.update_minecraft(guild) for guild in self.bot.guilds))

    @background.before_loop
    async def before_background(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Operations(bot))
