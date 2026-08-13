from pathlib import Path

import pytest

from nexoria.database import Database
from nexoria.domain import LEADERSHIP_SECTIONS


@pytest.mark.asyncio
async def test_settings_and_roles_are_isolated_by_guild(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    await db.connect()
    try:
        await db.set(1, "minecraft.address", "a.example")
        await db.set(2, "minecraft.address", "b.example")
        await db.replace_roles(1, "team.Owner", [10, 11])
        await db.replace_roles(2, "team.Owner", [20])
        assert await db.get(1, "minecraft.address") == "a.example"
        assert await db.get(2, "minecraft.address") == "b.example"
        assert await db.roles(1, "team.Owner") == {10, 11}
        assert await db.roles(2, "team.Owner") == {20}
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_default_leadership_structure_is_exact(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.sqlite3")
    await db.connect()
    try:
        await db.ensure_guild(1)
        rows = await db.rows(
            "SELECT name FROM leadership_sections WHERE guild_id=? ORDER BY position", (1,)
        )
        assert tuple(row["name"] for row in rows) == LEADERSHIP_SECTIONS
    finally:
        await db.close()
