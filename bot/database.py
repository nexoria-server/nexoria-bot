from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.execute("PRAGMA journal_mode = WAL")
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_config(
                guild_id INTEGER PRIMARY KEY,
                log_channel_id INTEGER DEFAULT 0,
                ticket_category_id INTEGER DEFAULT 0,
                application_channel_id INTEGER DEFAULT 0,
                ticket_staff_role_id INTEGER DEFAULT 0,
                application_staff_role_id INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS warnings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_warnings_guild_user
                ON warnings(guild_id, user_id, created_at);
            CREATE TABLE IF NOT EXISTS moderation_actions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                duration_seconds INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_moderation_guild_user
                ON moderation_actions(guild_id, user_id, created_at);
            CREATE TABLE IF NOT EXISTS team_members(
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                description TEXT DEFAULT '',
                PRIMARY KEY(guild_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS giveaways(
                message_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                prize TEXT NOT NULL,
                end_at REAL NOT NULL,
                winners INTEGER NOT NULL,
                ended INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS giveaway_entries(
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY(message_id,user_id),
                FOREIGN KEY(message_id) REFERENCES giveaways(message_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS minecraft_panels(
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                mode TEXT NOT NULL DEFAULT 'offen',
                payload_hash TEXT
            );
            """
        )
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None

    def _connection(self) -> aiosqlite.Connection:
        if self.conn is None:
            raise RuntimeError("Die Datenbank ist nicht verbunden.")
        return self.conn

    async def execute(self, query: str, parameters: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        connection = self._connection()
        cursor = await connection.execute(query, parameters)
        await connection.commit()
        return cursor

    async def fetchone(self, query: str, parameters: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        return await (await self._connection().execute(query, parameters)).fetchone()

    async def fetchall(self, query: str, parameters: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        return list(await (await self._connection().execute(query, parameters)).fetchall())

    async def guild_config(self, guild_id: int) -> aiosqlite.Row:
        row = await self.fetchone("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,))
        if row:
            return row
        await self.execute("INSERT INTO guild_config(guild_id) VALUES(?)", (guild_id,))
        row = await self.fetchone("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,))
        assert row is not None
        return row

    async def set_config(self, guild_id: int, field: str, value: int) -> None:
        allowed = {
            "log_channel_id",
            "ticket_category_id",
            "application_channel_id",
            "ticket_staff_role_id",
            "application_staff_role_id",
        }
        if field not in allowed:
            raise ValueError("Ungültiges Konfigurationsfeld")
        await self.guild_config(guild_id)
        await self.execute(
            f"UPDATE guild_config SET {field}=? WHERE guild_id=?", (value, guild_id)
        )
