from bot.services import DEFAULT_APPLICATION_TYPES, TEAM_LEVELS, highest_team_level


def test_requested_team_hierarchy_has_no_media() -> None:
    assert TEAM_LEVELS == (
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
    assert "Media" not in TEAM_LEVELS


def test_only_highest_team_role_is_selected() -> None:
    configured = {"Owner": {1}, "Developer": {2}, "Supporter": {3}}
    assert highest_team_level({2, 3}, configured) == "Developer"
    assert highest_team_level({1, 2, 3}, configured) == "Owner"
    assert highest_team_level({99}, configured) is None


def test_application_periods_match_requirements() -> None:
    assert DEFAULT_APPLICATION_TYPES["test_supporter"]["days"] == 30
    assert DEFAULT_APPLICATION_TYPES["test_developer"]["days"] == 14
    assert DEFAULT_APPLICATION_TYPES["media"]["days"] == 14
    assert DEFAULT_APPLICATION_TYPES["partner"]["days"] == 7
