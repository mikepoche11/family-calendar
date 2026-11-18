"""SQLite storage. One file, WAL mode, plain SQL."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL UNIQUE,
    color    TEXT NOT NULL,
    avatar   TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,          -- Google event id (instance id for recurring events)
    summary     TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    location    TEXT NOT NULL DEFAULT '',
    start       TEXT NOT NULL,             -- ISO datetime, or YYYY-MM-DD for all-day
    end         TEXT NOT NULL,
    all_day     INTEGER NOT NULL DEFAULT 0,
    person_id   INTEGER REFERENCES people(id) ON DELETE SET NULL,
    recurring   INTEGER NOT NULL DEFAULT 0,
    updated     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS events_start ON events(start);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)
            # Migrations for databases created by earlier versions
            cols = {r[1] for r in conn.execute("PRAGMA table_info(people)")}
            if "avatar" not in cols:
                conn.execute("ALTER TABLE people ADD COLUMN avatar TEXT NOT NULL DEFAULT ''")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- meta -------------------------------------------------------------
    def get_meta(self, key: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    # --- people -----------------------------------------------------------
    def seed_people(self, seed: str) -> None:
        """Insert people from 'Name:#color,...' only when the table is empty."""
        with self.connect() as conn:
            if conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]:
                return
            for pos, item in enumerate(p for p in seed.split(",") if p.strip()):
                name, _, color = item.partition(":")
                conn.execute(
                    "INSERT INTO people(name, color, position) VALUES(?, ?, ?)",
                    (name.strip(), (color.strip() or "#64748b"), pos),
                )

    def list_people(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT id, name, color, avatar, position FROM people ORDER BY position, id").fetchall()
        return [dict(r) for r in rows]

    def create_person(self, name: str, color: str, avatar: str = "") -> dict:
        with self.connect() as conn:
            pos = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM people").fetchone()[0]
            cur = conn.execute(
                "INSERT INTO people(name, color, avatar, position) VALUES(?, ?, ?, ?)", (name, color, avatar, pos)
            )
            pid = cur.lastrowid
        return {"id": pid, "name": name, "color": color, "avatar": avatar, "position": pos}

    def update_person(
        self, pid: int, name: str | None = None, color: str | None = None, avatar: str | None = None
    ) -> dict | None:
        with self.connect() as conn:
            for col, val in (("name", name), ("color", color), ("avatar", avatar)):
                if val is not None:
                    conn.execute(f"UPDATE people SET {col} = ? WHERE id = ?", (val, pid))
            row = conn.execute(
                "SELECT id, name, color, avatar, position FROM people WHERE id = ?", (pid,)
            ).fetchone()
        return dict(row) if row else None

    def delete_person(self, pid: int) -> bool:
        with self.connect() as conn:
            return conn.execute("DELETE FROM people WHERE id = ?", (pid,)).rowcount > 0

    # --- events -----------------------------------------------------------
    def replace_window(self, window_start: str, window_end: str, events: list[dict]) -> bool:
        """Replace every stored event overlapping the window with `events`.

        Returns True when anything changed, so the UI only refreshes when needed.
        """
        with self.connect() as conn:
            before = conn.execute(
                "SELECT id, summary, description, location, start, end, all_day, person_id, updated "
                "FROM events WHERE end > ? AND start < ? ORDER BY id",
                (window_start, window_end),
            ).fetchall()
            conn.execute("DELETE FROM events WHERE end > ? AND start < ?", (window_start, window_end))
            conn.executemany(
                "INSERT OR REPLACE INTO events(id, summary, description, location, start, end, all_day, "
                "person_id, recurring, updated) VALUES(:id, :summary, :description, :location, :start, :end, "
                ":all_day, :person_id, :recurring, :updated)",
                events,
            )
            after = conn.execute(
                "SELECT id, summary, description, location, start, end, all_day, person_id, updated "
                "FROM events WHERE end > ? AND start < ? ORDER BY id",
                (window_start, window_end),
            ).fetchall()
        return [tuple(r) for r in before] != [tuple(r) for r in after]

    def upsert_event(self, event: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO events(id, summary, description, location, start, end, all_day, "
                "person_id, recurring, updated) VALUES(:id, :summary, :description, :location, :start, :end, "
                ":all_day, :person_id, :recurring, :updated)",
                event,
            )

    def reassign_people(self, people: list[dict], matcher) -> None:
        """Recompute every event's owner after people were added, renamed or removed."""
        with self.connect() as conn:
            rows = conn.execute("SELECT id, summary FROM events").fetchall()
            conn.executemany(
                "UPDATE events SET person_id = ? WHERE id = ?",
                [(matcher(r["summary"], people), r["id"]) for r in rows],
            )

    def delete_event(self, event_id: str) -> bool:
        with self.connect() as conn:
            return conn.execute("DELETE FROM events WHERE id = ?", (event_id,)).rowcount > 0

    def get_event(self, event_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return _event_row(row) if row else None

    def list_events(self, start: str, end: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE end > ? AND start < ? ORDER BY start", (start, end)
            ).fetchall()
        return [_event_row(r) for r in rows]


def _event_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["all_day"] = bool(d["all_day"])
    d["recurring"] = bool(d["recurring"])
    return d
