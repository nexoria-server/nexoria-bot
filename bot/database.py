from __future__ import annotations

from pathlib import Path
import json
from collections.abc import Iterable
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
            CREATE TABLE IF NOT EXISTS guild_settings(
                guild_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY(guild_id,key)
            );
            CREATE TABLE IF NOT EXISTS role_bindings(
                guild_id INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY(guild_id,purpose,role_id)
            );
            CREATE INDEX IF NOT EXISTS idx_role_bindings_purpose
                ON role_bindings(guild_id,purpose);
            CREATE TABLE IF NOT EXISTS panel_messages(
                guild_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                payload_hash TEXT,
                PRIMARY KEY(guild_id,kind)
            );
            CREATE TABLE IF NOT EXISTS ticket_types(
                guild_id INTEGER NOT NULL,
                type_key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                emoji TEXT NOT NULL DEFAULT '🎫',
                category_id INTEGER DEFAULT 0,
                archive_channel_id INTEGER DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(guild_id,type_key)
            );
            CREATE TABLE IF NOT EXISTS tickets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER UNIQUE,
                owner_id INTEGER NOT NULL,
                type_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT,
                closed_by INTEGER,
                close_reason TEXT,
                transcript TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_search
                ON tickets(guild_id,owner_id,type_key,status,created_at);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_one_open
                ON tickets(guild_id,owner_id,type_key) WHERE status='open';
            CREATE TABLE IF NOT EXISTS application_types(
                guild_id INTEGER NOT NULL,
                type_key TEXT NOT NULL,
                name TEXT NOT NULL,
                test_days INTEGER NOT NULL DEFAULT 14,
                questions TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(guild_id,type_key)
            );
            CREATE TABLE IF NOT EXISTS applications(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                type_key TEXT NOT NULL,
                answers TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                reviewer_id INTEGER,
                decision_reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                decided_at TEXT,
                test_start TEXT,
                test_end TEXT,
                onboarding_sent_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_applications_search
                ON applications(guild_id,user_id,type_key,status,created_at);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_applications_one_open
                ON applications(guild_id,user_id,type_key) WHERE status='open';
            CREATE TABLE IF NOT EXISTS giveaway_winners(
                message_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                prize TEXT NOT NULL,
                claimed_at TEXT,
                ticket_id INTEGER,
                PRIMARY KEY(message_id,user_id)
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
        await self.execute(f"UPDATE guild_config SET {field}=? WHERE guild_id=?", (value, guild_id))

    async def setting(self, guild_id: int, key: str, default: Any = None) -> Any:
        row = await self.fetchone(
            "SELECT value FROM guild_settings WHERE guild_id=? AND key=?",
            (guild_id, key),
        )
        return json.loads(row["value"]) if row else default

    async def set_setting(self, guild_id: int, key: str, value: Any) -> None:
        await self.execute(
            "INSERT INTO guild_settings(guild_id,key,value) VALUES(?,?,?) "
            "ON CONFLICT(guild_id,key) DO UPDATE SET value=excluded.value",
            (guild_id, key, json.dumps(value, ensure_ascii=False)),
        )

    async def roles(self, guild_id: int, purpose: str) -> set[int]:
        rows = await self.fetchall(
            "SELECT role_id FROM role_bindings WHERE guild_id=? AND purpose=?",
            (guild_id, purpose),
        )
        return {int(row["role_id"]) for row in rows}

    async def replace_roles(self, guild_id: int, purpose: str, role_ids: Iterable[int]) -> None:
        connection = self._connection()
        await connection.execute(
            "DELETE FROM role_bindings WHERE guild_id=? AND purpose=?",
            (guild_id, purpose),
        )
        await connection.executemany(
            "INSERT INTO role_bindings(guild_id,purpose,role_id) VALUES(?,?,?)",
            [(guild_id, purpose, role_id) for role_id in set(role_ids)],
        )
        await connection.commit()

    async def role_map(self, guild_id: int, prefix: str) -> dict[str, set[int]]:
        rows = await self.fetchall(
            "SELECT purpose,role_id FROM role_bindings WHERE guild_id=? AND purpose LIKE ?",
            (guild_id, f"{prefix}%"),
        )
        result: dict[str, set[int]] = {}
        for row in rows:
            name = str(row["purpose"])[len(prefix) :]
            result.setdefault(name, set()).add(int(row["role_id"]))
        return result
