from nexoria.domain import TEAM_HIERARCHY, highest_team_level


def test_owner_is_first_and_test_supporter_last() -> None:
    assert TEAM_HIERARCHY[0] == "Owner"
    assert TEAM_HIERARCHY[-1] == "Test Supporter"
    assert "Media" not in TEAM_HIERARCHY


def test_member_only_appears_at_highest_level() -> None:
    configured = {
        "Owner": {1},
        "Admin": {2},
        "Developer": {3},
        "Supporter": {4},
    }
    assert highest_team_level({1, 2, 3, 4}, configured) == "Owner"
    assert highest_team_level({3, 4}, configured) == "Developer"
    assert highest_team_level({99}, configured) is None
