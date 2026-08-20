import importlib
from pathlib import Path

from main import BOT_ACTIVITY, COGS


def test_bot_activity_text() -> None:
    assert BOT_ACTIVITY == "NexoriaCraft.de on mc"


def test_all_configured_extensions_exist_and_import() -> None:
    assert "bot.cogs.announcments" in COGS
    assert "bot.cogs.invites" in COGS
    assert "bot.cogs.management" in COGS
    assert "bot.cogs.compatibility" in COGS
    assert "bot.cogs.command_center" in COGS
    assert "bot.cogs.team_system" in COGS
    assert "bot.cogs.team" not in COGS
    assert len(COGS) == len(set(COGS)) == 16
    for extension in COGS:
        assert importlib.import_module(extension)


def test_no_secret_or_runtime_data_is_tracked() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    for entry in (".env", "data/", "logs/", "*.db", "applications.json", "invites.json"):
        assert entry in gitignore
