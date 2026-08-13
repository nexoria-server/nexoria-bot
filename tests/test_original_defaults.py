from bot.cogs.team import TEAM_ROLES
from bot.config import settings


def test_original_team_structure_is_preserved() -> None:
    assert [name for _, name, _ in TEAM_ROLES] == [
        "Owner",
        "Co-Owner",
        "Admin",
        "Moderator ++",
        "Moderator",
        "Developer",
        "Builder",
        "Supporter",
        "Test Supporter",
        "Media",
    ]


def test_original_channel_defaults_are_preserved() -> None:
    assert settings.WELCOME_CHANNEL_ID == 1527098242284650578
    assert settings.TICKET_CATEGORY_ID == 1527354804899414056
    assert settings.APPLICATION_PANEL_CHANNEL_ID == 1529086680533831751
    assert settings.ANNOUNCEMENT_PANEL_CHANNEL_ID == 1535968109230301254
    assert settings.TEAM_PANEL_CHANNEL_ID == 1527222155996041307
