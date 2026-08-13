from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def int_env(name: str, default: int = 0) -> int:
    value = os.getenv(name, "").strip()
    try:
        return int(value) if value else default
    except ValueError:
        return default


def bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def id_set_env(name: str) -> frozenset[int]:
    result: set[int] = set()
    for value in os.getenv(name, "").split(","):
        value = value.strip()
        if value.isdigit():
            result.add(int(value))
    return frozenset(result)


def path_env(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    return Path(value) if value else default


@dataclass(frozen=True, slots=True)
class Settings:
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "").strip()
    DEV_GUILD_ID: int = int_env("DEV_GUILD_ID")
    BOT_STATUS: str = os.getenv("BOT_STATUS", "Nexoria Craft")

    MC_SERVER_HOST: str = os.getenv("MC_SERVER_HOST", "NexoriaCraft.de")
    MC_SERVER_PORT: int = int_env("MC_SERVER_PORT", 25565)
    MC_BEDROCK_HOST: str = os.getenv("MC_BEDROCK_HOST", "NexoriaCraft.de")
    MC_BEDROCK_PORT: int = int_env("MC_BEDROCK_PORT", 1932)
    MC_STATUS_CHANNEL_ID: int = int_env("MC_STATUS_CHANNEL_ID")
    MC_UPDATE_SECONDS: int = max(15, int_env("MC_UPDATE_SECONDS", 15))

    LOG_CHANNEL_ID: int = int_env("LOG_CHANNEL_ID")
    WELCOME_CHANNEL_ID: int = int_env("WELCOME_CHANNEL_ID")
    LEAVE_CHANNEL_ID: int = int_env("LEAVE_CHANNEL_ID")
    DISCORD_RULES_CHANNEL_ID: int = int_env("DISCORD_RULES_CHANNEL_ID")
    MINECRAFT_RULES_CHANNEL_ID: int = int_env("MINECRAFT_RULES_CHANNEL_ID")

    TICKET_CATEGORY_ID: int = int_env("TICKET_CATEGORY_ID")
    TICKET_STAFF_ROLE_ID: int = int_env("TICKET_STAFF_ROLE_ID")
    INVITE_PANEL_CHANNEL_ID: int = int_env("INVITE_PANEL_CHANNEL_ID")
    INVITE_CLAIM_CATEGORY_ID: int = int_env("INVITE_CLAIM_CATEGORY_ID")

    APPLICATION_PANEL_CHANNEL_ID: int = int_env("APPLICATION_PANEL_CHANNEL_ID")
    APPLICATION_CATEGORY_ID: int = int_env("APPLICATION_CATEGORY_ID")
    APPLICATION_LIST_CHANNEL_ID: int = int_env("APPLICATION_LIST_CHANNEL_ID")
    APPLICATION_SEARCH_CHANNEL_ID: int = int_env("APPLICATION_SEARCH_CHANNEL_ID")
    MEDIA_ROLE_ID: int = int_env("MEDIA_ROLE_ID")
    TEST_SUPPORTER_ROLE_ID: int = int_env("TEST_SUPPORTER_ROLE_ID")
    BUILDER_ROLE_ID: int = int_env("BUILDER_ROLE_ID")
    DEVELOPER_ROLE_ID: int = int_env("DEVELOPER_ROLE_ID")
    PARTNER_ROLE_ID: int = int_env("PARTNER_ROLE_ID")

    ANNOUNCEMENT_PANEL_CHANNEL_ID: int = int_env("ANNOUNCEMENT_PANEL_CHANNEL_ID")
    GIVEAWAY_CLAIM_CHANNEL_ID: int = int_env("GIVEAWAY_CLAIM_CHANNEL_ID")
    ANNOUNCEMENT_REQUIRE_ADMIN: bool = bool_env("ANNOUNCEMENT_REQUIRE_ADMIN", True)
    ANNOUNCEMENT_ALLOWED_ROLE_IDS: frozenset[int] = id_set_env(
        "ANNOUNCEMENT_ALLOWED_ROLE_IDS"
    )

    TEAM_PANEL_CHANNEL_ID: int = int_env("TEAM_PANEL_CHANNEL_ID")
    MOD_LOG_CHANNEL_ID: int = int_env("MOD_LOG_CHANNEL_ID")
    OWNER_ROLE_ID: int = int_env("OWNER_ROLE_ID")
    CO_OWNER_ROLE_ID: int = int_env("CO_OWNER_ROLE_ID")
    ADMIN_ROLE_ID: int = int_env("ADMIN_ROLE_ID")
    HEAD_DEVELOPER_ROLE_ID: int = int_env("HEAD_DEVELOPER_ROLE_ID")
    DEVELOPER_TEAM_ROLE_ID: int = int_env("DEVELOPER_TEAM_ROLE_ID")
    TEST_DEVELOPER_ROLE_ID: int = int_env("TEST_DEVELOPER_ROLE_ID")
    MODERATOR_PLUS_ROLE_ID: int = int_env("MODERATOR_PLUS_ROLE_ID")
    MODERATOR_ROLE_ID: int = int_env("MODERATOR_ROLE_ID")
    SUPPORTER_ROLE_ID: int = int_env("SUPPORTER_ROLE_ID")
    TEST_SUPPORTER_TEAM_ROLE_ID: int = int_env("TEST_SUPPORTER_TEAM_ROLE_ID")

    DB_PATH: Path = path_env("DB_PATH", BASE_DIR / "data" / "bot.db")
    TEAM_DB_PATH: Path = path_env("TEAM_DB_PATH", BASE_DIR / "data" / "team_panel.db")
    DATA_DIR: Path = path_env("DATA_DIR", BASE_DIR / "data")
    LOG_DIR: Path = path_env("LOG_DIR", BASE_DIR / "logs")


settings = Settings()
