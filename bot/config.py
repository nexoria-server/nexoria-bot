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
    WELCOME_CHANNEL_ID: int = int_env("WELCOME_CHANNEL_ID", 1527098242284650578)
    LEAVE_CHANNEL_ID: int = int_env("LEAVE_CHANNEL_ID", 1535726476769501194)
    DISCORD_RULES_CHANNEL_ID: int = int_env(
        "DISCORD_RULES_CHANNEL_ID", 1527098242284650579
    )
    MINECRAFT_RULES_CHANNEL_ID: int = int_env(
        "MINECRAFT_RULES_CHANNEL_ID", 1535734820284399697
    )

    TICKET_CATEGORY_ID: int = int_env("TICKET_CATEGORY_ID", 1527354804899414056)
    TICKET_STAFF_ROLE_ID: int = int_env("TICKET_STAFF_ROLE_ID", 1528081526934212839)
    INVITE_PANEL_CHANNEL_ID: int = int_env(
        "INVITE_PANEL_CHANNEL_ID", 1527111245998854335
    )
    INVITE_CLAIM_CATEGORY_ID: int = int_env("INVITE_CLAIM_CATEGORY_ID")

    APPLICATION_PANEL_CHANNEL_ID: int = int_env(
        "APPLICATION_PANEL_CHANNEL_ID", 1529086680533831751
    )
    APPLICATION_CATEGORY_ID: int = int_env(
        "APPLICATION_CATEGORY_ID", 1535739435805581423
    )
    APPLICATION_LIST_CHANNEL_ID: int = int_env(
        "APPLICATION_LIST_CHANNEL_ID", 1535748337037479956
    )
    APPLICATION_SEARCH_CHANNEL_ID: int = int_env(
        "APPLICATION_SEARCH_CHANNEL_ID", 1535749442601230437
    )
    MEDIA_ROLE_ID: int = int_env("MEDIA_ROLE_ID", 1527099952730345574)
    TEST_SUPPORTER_ROLE_ID: int = int_env(
        "TEST_SUPPORTER_ROLE_ID", 1527099612274364638
    )
    BUILDER_ROLE_ID: int = int_env("BUILDER_ROLE_ID", 1528052296099823808)
    DEVELOPER_ROLE_ID: int = int_env("DEVELOPER_ROLE_ID", 1527099942446039040)
    PARTNER_ROLE_ID: int = int_env("PARTNER_ROLE_ID", 1528510196144672882)

    ANNOUNCEMENT_PANEL_CHANNEL_ID: int = int_env(
        "ANNOUNCEMENT_PANEL_CHANNEL_ID", 1535968109230301254
    )
    GIVEAWAY_CLAIM_CHANNEL_ID: int = int_env(
        "GIVEAWAY_CLAIM_CHANNEL_ID", 1536097487364948030
    )
    ANNOUNCEMENT_REQUIRE_ADMIN: bool = bool_env("ANNOUNCEMENT_REQUIRE_ADMIN", True)
    ANNOUNCEMENT_ALLOWED_ROLE_IDS: frozenset[int] = id_set_env(
        "ANNOUNCEMENT_ALLOWED_ROLE_IDS"
    )

    TEAM_PANEL_CHANNEL_ID: int = int_env("TEAM_PANEL_CHANNEL_ID", 1527222155996041307)
    MOD_LOG_CHANNEL_ID: int = int_env("MOD_LOG_CHANNEL_ID", 1527107932938965138)
    OWNER_ROLE_ID: int = int_env("OWNER_ROLE_ID", 1527101544351142128)
    CO_OWNER_ROLE_ID: int = int_env("CO_OWNER_ROLE_ID", 1527112990758015016)
    ADMIN_ROLE_ID: int = int_env("ADMIN_ROLE_ID", 1527099723629203556)
    HEAD_DEVELOPER_ROLE_ID: int = int_env("HEAD_DEVELOPER_ROLE_ID")
    DEVELOPER_TEAM_ROLE_ID: int = int_env(
        "DEVELOPER_TEAM_ROLE_ID", 1527099942446039040
    )
    TEST_DEVELOPER_ROLE_ID: int = int_env("TEST_DEVELOPER_ROLE_ID")
    MODERATOR_PLUS_ROLE_ID: int = int_env(
        "MODERATOR_PLUS_ROLE_ID", 1527299075060404344
    )
    MODERATOR_ROLE_ID: int = int_env("MODERATOR_ROLE_ID", 1527099725369839756)
    SUPPORTER_ROLE_ID: int = int_env("SUPPORTER_ROLE_ID", 1527099685125492826)
    TEST_SUPPORTER_TEAM_ROLE_ID: int = int_env(
        "TEST_SUPPORTER_TEAM_ROLE_ID", 1527099612274364638
    )
    BUILDER_TEAM_ROLE_ID: int = int_env("BUILDER_TEAM_ROLE_ID", 1528052296099823808)
    MEDIA_TEAM_ROLE_ID: int = int_env("MEDIA_TEAM_ROLE_ID", 1527099952730345574)

    DB_PATH: Path = path_env("DB_PATH", BASE_DIR / "data" / "bot.db")
    TEAM_DB_PATH: Path = path_env("TEAM_DB_PATH", BASE_DIR / "data" / "team_panel.db")
    DATA_DIR: Path = path_env("DATA_DIR", BASE_DIR / "data")
    LOG_DIR: Path = path_env("LOG_DIR", BASE_DIR / "logs")


settings = Settings()
