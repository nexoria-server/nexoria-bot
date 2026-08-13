
import discord
from discord import app_commands
from discord.ext import commands


DISCORD_RULES_CHANNEL_ID = 1527098242284650579
MINECRAFT_RULES_CHANNEL_ID = 1535734820284399697


DISCORD_RULES = discord.Embed(
    title="📜 NexoriaCraft – Discord-Regeln",
    description=(
        "Damit auf **NexoriaCraft** alles fair, entspannt und "
        "respektvoll abläuft, bitten wir euch, folgende Regeln "
        "einzuhalten.\n\n"

        "**1. 🤝 Respektvoller Umgang**\n"
        "Beleidigungen, Provokationen und respektloses Verhalten "
        "gegenüber anderen Spielern oder dem Team werden nicht toleriert.\n\n"

        "**2. 🚫 Unangemessene Inhalte**\n"
        "Sexuelle Anmachen, sexuelle Angebote oder andere "
        "unangemessene Inhalte sind im Chat strengstens verboten.\n\n"

        "**3. 💬 Chat & Spam**\n"
        "Spam, Flooding, unnötige Nachrichten oder absichtliches "
        "Stören des Chats sind verboten.\n\n"

        "**4. 📢 Werbung**\n"
        "Unerlaubte Werbung für andere Server, Projekte oder "
        "Communities ist nicht gestattet.\n\n"

        "**5. 🔔 Teammitglieder & Pings**\n"
        "Teammitglieder dürfen nicht unnötig gepingt oder "
        "öffentlich belästigt werden. Nutzt bei Problemen bitte "
        "den vorgesehenen Support.\n\n"

        "**6. 🎫 Tickets & Support**\n"
        "Eröffnet nicht mehrere Tickets gleichzeitig. Das behindert "
        "den Support und sorgt nur für längere Wartezeiten.\n\n"

        "**7. 🛡️ Umgang mit dem Team**\n"
        "Behandelt das gesamte Team immer mit Respekt.\n\n"

        "**8. 🔐 Privatsphäre**\n"
        "Private Daten von euch oder anderen Personen dürfen "
        "nicht ohne Erlaubnis veröffentlicht werden.\n\n"

        "**9. ⚠️ Konsequenzen**\n"
        "Verstöße können je nach Schwere mit Verwarnungen, "
        "Timeouts, Kicks oder Bans geahndet werden.\n\n"

        "**📖 Wichtig**\n"
        "Bitte lest euch die Regeln vollständig durch."
    ),
    color=discord.Color.blurple(),
)

DISCORD_RULES.set_footer(
    text="NexoriaCraft • Discord-Regelwerk"
)


MINECRAFT_RULES = discord.Embed(
    title="⛏️ NexoriaCraft – Minecraft-Regeln",
    description=(
        "Damit **NexoriaCraft** für alle fair und angenehm bleibt, "
        "gelten folgende Regeln.\n\n"

        "**1. 💬 Kein Spam im Chat**\n"
        "Wiederholte Nachrichten, unnötige Zeichenfolgen oder "
        "dauerhaftes Spammen sind verboten.\n\n"

        "**2. 🗣️ Keine Provokationen**\n"
        "Andere Spieler absichtlich zu reizen, Streit anzufangen "
        "oder die Stimmung zu stören, ist nicht erlaubt.\n\n"

        "**3. 🤝 Keine Beleidigungen**\n"
        "Respektloses, beleidigendes oder diskriminierendes Verhalten "
        "wird nicht toleriert.\n\n"

        "**4. 🚫 Keine sexuellen oder unangemessenen Inhalte**\n"
        "Sexuelle Anmachen, sexuelle Angebote oder andere "
        "unangemessene Nachrichten sind verboten.\n\n"

        "**5. 🛡️ Teammitglieder dürfen nicht angebettelt werden**\n"
        "Es ist verboten, Teammitglieder nach Items, Ingame-Geld, "
        "Rängen, Sonderrechten oder anderen Vorteilen zu fragen.\n\n"

        "**6. 💶 Kein Echtgeldhandel**\n"
        "Items, Ingame-Geld, Accounts oder andere Vorteile dürfen "
        "nicht gegen echtes Geld verkauft oder angeboten werden.\n\n"

        "**7. 🐛 Kein Ausnutzen von Bugs oder Fehlern**\n"
        "Fehler müssen dem Team gemeldet werden und dürfen nicht "
        "zum eigenen Vorteil genutzt werden.\n\n"

        "**8. ⚔️ Fair Play ist Pflicht**\n"
        "Cheats, Hacks oder andere unerlaubte Hilfsmittel sind verboten.\n\n"

        "**⚠️ Wichtig**\n"
        "Bitte lest euch die Regeln vollständig durch.\n\n"

        "Wer gegen die Regeln verstößt, muss je nach Schwere "
        "des Verstoßes mit Verwarnungen, Mutes, Kicks oder Bans rechnen."
    ),
    color=discord.Color.green(),
)

MINECRAFT_RULES.set_footer(
    text="NexoriaCraft • Minecraft-Regelwerk"
)


class Rules(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="regeln",
        description="Postet das gewünschte NexoriaCraft-Regelwerk.",
    )
    @app_commands.describe(
        bereich="Welches Regelwerk soll gepostet werden?"
    )
    @app_commands.choices(
        bereich=[
            app_commands.Choice(
                name="Discord",
                value="discord",
            ),
            app_commands.Choice(
                name="Minecraft",
                value="minecraft",
            ),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def regeln(
        self,
        interaction: discord.Interaction,
        bereich: app_commands.Choice[str],
    ):

        if bereich.value == "discord":
            channel_id = DISCORD_RULES_CHANNEL_ID
            embed = DISCORD_RULES.copy()
        else:
            channel_id = MINECRAFT_RULES_CHANNEL_ID
            embed = MINECRAFT_RULES.copy()

        channel = interaction.guild.get_channel(channel_id)

        if channel is None:
            await interaction.response.send_message(
                "❌ Der konfigurierte Regelkanal wurde nicht gefunden.",
                ephemeral=True,
            )
            return

        await channel.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Das **{bereich.name}-Regelwerk** wurde in "
            f"{channel.mention} gepostet.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Rules(bot))
