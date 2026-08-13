from __future__ import annotations

from collections.abc import Iterable, Mapping

TEAM_HIERARCHY = (
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

LEADERSHIP_SECTIONS = (
    "Team-Leitung",
    "Mentoren",
    "Developer-Leitung",
    "Builder-Leitung",
    "Media-Leitung",
    "Partner-Leitung",
)

APPLICATION_DEFAULT_DAYS = {
    "Test Supporter": 30,
    "Test Developer": 14,
    "Partner": 7,
    "Media": 14,
}


def highest_team_level(
    member_role_ids: Iterable[int], configured: Mapping[str, set[int]]
) -> str | None:
    """Return exactly one level; hierarchy order is the priority contract."""
    owned = set(member_role_ids)
    return next((level for level in TEAM_HIERARCHY if owned & configured.get(level, set())), None)
