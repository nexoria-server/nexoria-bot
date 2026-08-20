from pathlib import Path

import pytest

from bot.database import Database


@pytest.mark.asyncio
async def test_database_is_created_and_guilds_are_isolated(tmp_path: Path) -> None:
    database = Database(tmp_path / "nested" / "bot.db")
    await database.connect()
    try:
        await database.set_config(1, "log_channel_id", 111)
        await database.set_config(2, "log_channel_id", 222)
        assert (await database.guild_config(1))["log_channel_id"] == 111
        assert (await database.guild_config(2))["log_channel_id"] == 222
        tables = {
            row["name"]
            for row in await database.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {
            "moderation_actions",
            "minecraft_panels",
            "giveaways",
            "guild_settings",
            "role_bindings",
            "panel_messages",
            "tickets",
            "applications",
            "giveaway_winners",
        } <= tables

        await database.set_setting(1, "channel.logs", 123)
        assert await database.setting(1, "channel.logs") == 123
        await database.replace_roles(1, "team.Owner", [10, 20, 20])
        assert await database.roles(1, "team.Owner") == {10, 20}
    finally:
        await database.close()
