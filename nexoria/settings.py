from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    database_path: Path
    log_level: str

    @classmethod
    def load(cls) -> Settings:
        load_dotenv()
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN fehlt. Bitte .env.example als .env kopieren.")
        return cls(
            token=token,
            database_path=Path(os.getenv("DATABASE_PATH", "data/nexoria.sqlite3")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
