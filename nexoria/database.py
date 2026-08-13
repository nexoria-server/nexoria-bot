from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import aiosqlite

from .domain import APPLICATION_DEFAULT_DAYS, LEADERSHIP_SECTIONS, TEAM_HIERARCHY

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS guild_settings (
  guild_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
  PRIMARY KEY (guild_id, key)
);
CREATE TABLE IF NOT EXISTS role_bindings (
  guild_id INTEGER NOT NULL, purpose TEXT NOT NULL, role_id INTEGER NOT NULL,
  PRIMARY KEY (guild_id, purpose, role_id)
);
CREATE TABLE IF NOT EXISTS panels (
  guild_id INTEGER NOT NULL, kind TEXT NOT NULL, channel_id INTEGER NOT NULL,
  message_id INTEGER, payload_hash TEXT,
  PRIMARY KEY (guild_id, kind)
);
CREATE TABLE IF NOT EXISTS moderation_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
  actor_id INTEGER NOT NULL, target_id INTEGER NOT NULL, action TEXT NOT NULL,
  reason TEXT NOT NULL, duration_seconds INTEGER, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mod_target ON moderation_actions(guild_id, target_id, created_at);
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
  channel_id INTEGER UNIQUE, owner_id INTEGER NOT NULL, type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL, closed_at TEXT,
  closed_by INTEGER, transcript TEXT
);
CREATE INDEX IF NOT EXISTS idx_ticket_search ON tickets(guild_id, owner_id, type, status);
CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL, type TEXT NOT NULL, answers TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open', reviewer_id INTEGER, reason TEXT,
  created_at TEXT NOT NULL, decided_at TEXT, test_start TEXT, test_end TEXT,
  onboarding_sent_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_application_search ON applications(guild_id, user_id, type, status);
CREATE TABLE IF NOT EXISTS leadership_sections (
  guild_id INTEGER NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  position INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (guild_id, name)
);
CREATE TABLE IF NOT EXISTS giveaways (
  id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
  channel_id INTEGER NOT NULL, message_id INTEGER, prize TEXT NOT NULL,
  ends_at TEXT NOT NULL, winner_id INTEGER, status TEXT NOT NULL DEFAULT 'open'
);
CREATE TABLE IF NOT EXISTS giveaway_entries (
  giveaway_id INTEGER NOT NULL REFERENCES giveaways(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL, PRIMARY KEY(giveaway_id, user_id)
);
CREATE TABLE IF NOT EXISTS giveaway_claims (
  giveaway_id INTEGER NOT NULL REFERENCES giveaways(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL, ticket_id INTEGER, PRIMARY KEY(giveaway_id, user_id)
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.executescript(SCHEMA)
        await self.connection.commit()

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()

    @property
    def db(self) -> aiosqlite.Connection:
        if not self.connection:
            raise RuntimeError("Database is not connected")
        return self.connection

    async def ensure_guild(self, guild_id: int) -> None:
        await self.db.executemany(
            "INSERT OR IGNORE INTO leadership_sections(guild_id,name,position) VALUES(?,?,?)",
            [(guild_id, name, index) for index, name in enumerate(LEADERSHIP_SECTIONS)],
        )
        for level in TEAM_HIERARCHY:
            await self.set_default(guild_id, f"team.enabled.{level}", True)
        for name, days in APPLICATION_DEFAULT_DAYS.items():
            await self.set_default(guild_id, f"application.days.{name}", days)
        await self.db.commit()

    async def set_default(self, guild_id: int, key: str, value: Any) -> None:
        await self.db.execute(
            "INSERT OR IGNORE INTO guild_settings(guild_id,key,value) VALUES(?,?,?)",
            (guild_id, key, json.dumps(value, ensure_ascii=False)),
        )

    async def get(self, guild_id: int, key: str, default: Any = None) -> Any:
        row = await (
            await self.db.execute(
                "SELECT value FROM guild_settings WHERE guild_id=? AND key=?", (guild_id, key)
            )
        ).fetchone()
        return json.loads(row[0]) if row else default

    async def set(self, guild_id: int, key: str, value: Any) -> None:
        await self.db.execute(
            "INSERT INTO guild_settings(guild_id,key,value) VALUES(?,?,?) "
            "ON CONFLICT(guild_id,key) DO UPDATE SET value=excluded.value",
            (guild_id, key, json.dumps(value, ensure_ascii=False)),
        )
        await self.db.commit()

    async def roles(self, guild_id: int, purpose: str) -> set[int]:
        rows = await (
            await self.db.execute(
                "SELECT role_id FROM role_bindings WHERE guild_id=? AND purpose=?",
                (guild_id, purpose),
            )
        ).fetchall()
        return {int(row[0]) for row in rows}

    async def replace_roles(self, guild_id: int, purpose: str, role_ids: Iterable[int]) -> None:
        await self.db.execute(
            "DELETE FROM role_bindings WHERE guild_id=? AND purpose=?", (guild_id, purpose)
        )
        await self.db.executemany(
            "INSERT INTO role_bindings(guild_id,purpose,role_id) VALUES(?,?,?)",
            [(guild_id, purpose, role_id) for role_id in set(role_ids)],
        )
        await self.db.commit()

    async def configured_roles(self, guild_id: int, prefix: str) -> dict[str, set[int]]:
        rows = await (
            await self.db.execute(
                "SELECT purpose,role_id FROM role_bindings WHERE guild_id=? AND purpose LIKE ?",
                (guild_id, f"{prefix}%"),
            )
        ).fetchall()
        result: dict[str, set[int]] = {}
        for purpose, role_id in rows:
            result.setdefault(str(purpose)[len(prefix) :], set()).add(int(role_id))
        return result

    async def execute(self, sql: str, parameters: tuple[Any, ...] = ()) -> int:
        cursor = await self.db.execute(sql, parameters)
        await self.db.commit()
        return int(cursor.lastrowid or 0)

    async def rows(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        return list(await (await self.db.execute(sql, parameters)).fetchall())
