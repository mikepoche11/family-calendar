"""Chores: a list of recurring chores per person (or for anyone), checked off per day.

A chore repeats on chosen weekdays ("days": digits 0-6, Monday = 0; "0123456" = every day).
A completion is (chore, local date, who did it).
"""

from __future__ import annotations

from datetime import date

from .db import Database

SCHEMA = """
CREATE TABLE IF NOT EXISTS chores (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title     TEXT NOT NULL,
    icon      TEXT NOT NULL DEFAULT '',
    person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,  -- NULL = anyone can do it
    days      TEXT NOT NULL DEFAULT '0123456',
    position  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS chore_done (
    chore_id  INTEGER NOT NULL REFERENCES chores(id) ON DELETE CASCADE,
    day       TEXT NOT NULL,                                     -- local YYYY-MM-DD
    person_id INTEGER REFERENCES people(id) ON DELETE SET NULL,  -- who did it
    done_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (chore_id, day)
);
"""

# Starter set proposed in the plan; "each" = one copy per chosen kid, "anyone" = shared
STARTER = [
    ("Make bed", "🛏️", "each", "0123456"),
    ("Dirty clothes in the hamper", "🧺", "each", "0123456"),
    ("Clear your plate after dinner", "🍽️", "each", "0123456"),
    ("Tidy bedroom", "🧸", "each", "5"),
    ("Put away clean laundry", "👕", "each", "0123456"),
    ("Set the table", "🥄", "anyone", "0123456"),
    ("Unload the dishwasher", "🫧", "anyone", "0123456"),
    ("Take out the trash", "🗑️", "anyone", "0123456"),
]

COLS = "id, title, icon, person_id, days, position"


class Chores:
    def __init__(self, db: Database):
        self.db = db
        with db.connect() as conn:
            conn.executescript(SCHEMA)

    def list(self) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(f"SELECT {COLS} FROM chores ORDER BY position, id").fetchall()
        return [dict(r) for r in rows]

    def create(self, title: str, icon: str, person_id: int | None, days: str) -> dict:
        with self.db.connect() as conn:
            pos = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM chores").fetchone()[0]
            cid = conn.execute(
                "INSERT INTO chores(title, icon, person_id, days, position) VALUES(?, ?, ?, ?, ?)",
                (title, icon, person_id, _norm_days(days), pos),
            ).lastrowid
            return dict(conn.execute(f"SELECT {COLS} FROM chores WHERE id = ?", (cid,)).fetchone())

    def update(self, cid: int, fields: dict) -> dict | None:
        allowed = {k: v for k, v in fields.items() if k in ("title", "icon", "person_id", "days")}
        if "days" in allowed:
            allowed["days"] = _norm_days(allowed["days"])
        with self.db.connect() as conn:
            for k, v in allowed.items():
                conn.execute(f"UPDATE chores SET {k} = ? WHERE id = ?", (v, cid))
            row = conn.execute(f"SELECT {COLS} FROM chores WHERE id = ?", (cid,)).fetchone()
        return dict(row) if row else None

    def delete(self, cid: int) -> bool:
        with self.db.connect() as conn:
            return conn.execute("DELETE FROM chores WHERE id = ?", (cid,)).rowcount > 0

    def add_starter(self, kid_ids: list[int]) -> int:
        n = 0
        for title, icon, who, days in STARTER:
            if who == "each":
                for pid in kid_ids:
                    self.create(title, icon, pid, days)
                    n += 1
            else:
                self.create(title, icon, None, days)
                n += 1
        return n

    def for_day(self, day: date) -> list[dict]:
        """Chores scheduled on `day`, each with done / done_by for that day."""
        dow = str(day.weekday())
        key = day.isoformat()
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT c.id, c.title, c.icon, c.person_id, c.days, c.position, "
                f"d.person_id AS done_by, d.done_at FROM chores c "
                f"LEFT JOIN chore_done d ON d.chore_id = c.id AND d.day = ? "
                f"WHERE instr(c.days, ?) > 0 ORDER BY c.position, c.id",
                (key, dow),
            ).fetchall()
        return [dict(r) | {"done": r["done_at"] is not None} for r in rows]

    def set_done(self, cid: int, day: date, done: bool, person_id: int | None) -> bool:
        with self.db.connect() as conn:
            chore = conn.execute("SELECT person_id FROM chores WHERE id = ?", (cid,)).fetchone()
            if chore is None:
                return False
            if done:
                who = chore["person_id"] if chore["person_id"] is not None else person_id
                conn.execute(
                    "INSERT INTO chore_done(chore_id, day, person_id) VALUES(?, ?, ?) "
                    "ON CONFLICT(chore_id, day) DO UPDATE SET person_id = excluded.person_id",
                    (cid, day.isoformat(), who),
                )
            else:
                conn.execute("DELETE FROM chore_done WHERE chore_id = ? AND day = ?", (cid, day.isoformat()))
        return True


def _norm_days(days: str) -> str:
    d = "".join(sorted({c for c in days if c in "0123456"}))
    if not d:
        raise ValueError("Pick at least one day")
    return d
