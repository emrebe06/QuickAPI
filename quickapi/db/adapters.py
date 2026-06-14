from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class DatabaseAdapter(Protocol):
    name: str

    def health(self) -> dict[str, Any]:
        ...


@dataclass
class SQLiteAdapter:
    path: str | Path
    name: str = "sqlite"

    def connect(self):
        return sqlite3.connect(str(self.path))

    def health(self) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("select 1").fetchone()
        return {"ok": row == (1,), "driver": "sqlite3", "path": str(self.path)}

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]


@dataclass
class MongoAdapter:
    uri: str
    database: str
    name: str = "mongo"

    def client(self):
        try:
            from pymongo import MongoClient
        except ImportError as exc:
            raise RuntimeError("Install pymongo to use MongoAdapter: pip install pymongo") from exc
        return MongoClient(self.uri)

    def health(self) -> dict[str, Any]:
        client = self.client()
        client.admin.command("ping")
        return {"ok": True, "driver": "pymongo", "database": self.database}


@dataclass
class SQLAlchemyAdapter:
    url: str
    name: str = "sqlalchemy"

    def engine(self):
        try:
            from sqlalchemy import create_engine
        except ImportError as exc:
            raise RuntimeError("Install SQLAlchemy to use SQLAlchemyAdapter: pip install sqlalchemy") from exc
        return create_engine(self.url, pool_pre_ping=True)

    def health(self) -> dict[str, Any]:
        from sqlalchemy import text

        with self.engine().connect() as conn:
            row = conn.execute(text("select 1")).fetchone()
        return {"ok": bool(row), "driver": "sqlalchemy", "url": self.url.split("@")[-1]}


class DatabaseRegistry:
    def __init__(self):
        self._adapters: dict[str, DatabaseAdapter] = {}

    def register(self, name: str, adapter: DatabaseAdapter):
        self._adapters[name] = adapter
        return adapter

    def get(self, name: str) -> DatabaseAdapter | None:
        return self._adapters.get(name)

    def health(self) -> dict[str, Any]:
        result = {}
        for name, adapter in self._adapters.items():
            try:
                result[name] = adapter.health()
            except Exception as exc:
                result[name] = {"ok": False, "type": exc.__class__.__name__, "message": str(exc)}
        return result

    def list(self) -> list[str]:
        return sorted(self._adapters)
