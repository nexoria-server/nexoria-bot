from __future__ import annotations

import html
from datetime import UTC, datetime

import discord

TEAM_LEVELS = (
    "Owner",
    "Co-Owner",
    "Admin",
    "Head Developer",
    "Developer",
    "Test Developer",
    "Moderator+",
    "Moderator",
    "Supporter",
    "Test Supporter",
)

DEFAULT_TICKET_TYPES = {
    "support": ("Support", "Allgemeine Fragen und Hilfe", "🎫"),
    "application": ("Bewerbung", "Fragen zu Bewerbungen", "📝"),
    "media": ("Media", "Anliegen für das Media-Team", "🎥"),
    "partner": ("Partner", "Partnerschaften und Projekte", "🤝"),
    "team": ("Team", "Interne Team-Anliegen", "👥"),
    "giveaway": ("Giveaway", "Gewinn und Übergabe", "🎁"),
}

DEFAULT_APPLICATION_TYPES = {
    "test_supporter": {
        "name": "Test Supporter",
        "days": 30,
        "questions": (
            "Minecraft-Name\nDiscord-Name\nAlter\nSupport-Erfahrung\n"
            "Motivation\nUmgang mit Konflikten\nWöchentliche Aktivität"
        ),
    },
    "test_developer": {
        "name": "Test Developer",
        "days": 14,
        "questions": (
            "Minecraft-Name\nDiscord-Name\nAlter\nProgrammiersprachen\n"
            "Erfahrung und Projekte\nGitHub-/Portfolio-Link\nMotivation\nVerfügbarkeit"
        ),
    },
    "developer": {
        "name": "Developer",
        "days": 14,
        "questions": (
            "Minecraft-Name\nDiscord-Name\nAlter\nProgrammiersprachen\n"
            "Erfahrung und Projekte\nGitHub-/Portfolio-Link\nMotivation\nVerfügbarkeit"
        ),
    },
    "builder": {
        "name": "Builder",
        "days": 14,
        "questions": (
            "Minecraft-Name\nDiscord-Name\nAlter\nBaustile und Erfahrung\n"
            "WorldEdit-/Tool-Erfahrung\nPortfolio-/Bilder-Link\nMotivation\nVerfügbarkeit"
        ),
    },
    "media": {
        "name": "Media",
        "days": 14,
        "questions": (
            "Minecraft-Name\nDiscord-Name\nPlattform\nKanal-/Profil-Link\n"
            "Follower oder Abonnenten\nDurchschnittliche Videoaufrufe\n"
            "Aufrufe der letzten relevanten Videos\nUpload-Häufigkeit\n"
            "Vorhandener Nexoria-Craft-Content mit Links\n"
            "Geplanter Nexoria-Craft-Content\nMotivation"
        ),
    },
    "partner": {
        "name": "Partner",
        "days": 7,
        "questions": (
            "Projekt-/Servername\nAnsprechpartner\nDiscord-Link\n"
            "Minecraft-Serveradresse\nWebsite oder Projekt-Link\nMitgliederzahl\n"
            "Durchschnittlich aktive Mitglieder\nProjektbeschreibung\n"
            "Bestehende Partnerschaften\nGewünschte Zusammenarbeit\n"
            "Gegenseitiger Nutzen"
        ),
    },
}


async def ensure_guild_defaults(database, guild_id: int) -> None:
    await database._connection().executemany(
        "INSERT OR IGNORE INTO ticket_types("
        "guild_id,type_key,name,description,emoji) VALUES(?,?,?,?,?)",
        [
            (guild_id, key, name, description, emoji)
            for key, (name, description, emoji) in DEFAULT_TICKET_TYPES.items()
        ],
    )
    await database._connection().executemany(
        "INSERT OR IGNORE INTO application_types("
        "guild_id,type_key,name,test_days,questions) VALUES(?,?,?,?,?)",
        [
            (guild_id, key, value["name"], value["days"], value["questions"])
            for key, value in DEFAULT_APPLICATION_TYPES.items()
        ],
    )
    await database._connection().commit()


async def has_permission(interaction: discord.Interaction, database, purpose: str) -> bool:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    role_ids = await database.roles(interaction.guild.id, f"permission.{purpose}")
    return bool(role_ids & {role.id for role in interaction.user.roles})


async def require_permission(interaction: discord.Interaction, database, purpose: str) -> bool:
    if await has_permission(interaction, database, purpose):
        return True
    message = "❌ Du hast keine Berechtigung für diese Aktion."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
    return False


def highest_team_level(role_ids: set[int], configured: dict[str, set[int]]) -> str | None:
    return next(
        (level for level in TEAM_LEVELS if role_ids & configured.get(level, set())),
        None,
    )


async def safe_dm(user: discord.abc.Messageable, embed: discord.Embed) -> bool:
    try:
        await user.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


def transcript_html(messages: list[discord.Message], title: str) -> str:
    lines = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>{html.escape(title)}</title>",
        "<style>body{font-family:sans-serif;background:#111;color:#eee;padding:24px}"
        ".m{margin:12px 0;padding:10px;background:#222;border-radius:8px}"
        ".a{font-weight:bold}.t{color:#999;font-size:12px}</style></head><body>",
        f"<h1>{html.escape(title)}</h1>",
    ]
    for message in messages:
        content = html.escape(message.clean_content)
        attachments = " ".join(
            f"<a href='{html.escape(attachment.url)}'>Anhang</a>"
            for attachment in message.attachments
        )
        lines.append(
            "<div class='m'><span class='a'>"
            f"{html.escape(str(message.author))}</span> "
            f"<span class='t'>{message.created_at.astimezone(UTC).isoformat()}</span>"
            f"<br>{content}<br>{attachments}</div>"
        )
    lines.append(f"<footer>Exportiert {datetime.now(UTC).isoformat()}</footer></body></html>")
    return "".join(lines)
