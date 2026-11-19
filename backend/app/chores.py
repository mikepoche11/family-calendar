"""Chores: a list of recurring chores per person (or for anyone), checked off per day.

A chore repeats on chosen weekdays ("days": digits 0-6, Monday = 0; "0123456" = every day).
A completion is (chore, local date, who did it).

A chore can be worth blue marbles. When it is checked off, the person who did it gets them in
their marble jar (if they have one); unchecking it takes them back.
"""

from __future__ import annotations

from datetime import date

from .db import Database
from .marbles import Marbles

SCHEMA = """
CREATE TABLE IF NOT EXISTS chores (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title     TEXT NOT NULL,
    icon      TEXT NOT NULL DEFAULT '',
    person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,  -- NULL = anyone can do it
    days      TEXT NOT NULL DEFAULT '0123456',
    position  INTEGER NOT NULL DEFAULT 0,
    marbles   INTEGER NOT NULL DEFAULT 0                         -- blue marbles earned when done
);
CREATE TABLE IF NOT EXISTS chore_done (
    chore_id  INTEGER NOT NULL REFERENCES chores(id) ON DELETE CASCADE,
    day       TEXT NOT NULL,                                     -- local YYYY-MM-DD
    person_id INTEGER REFERENCES people(id) ON DELETE SET NULL,  -- who did it
    done_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    marbles   INTEGER NOT NULL DEFAULT 0,                        -- blue marbles actually given
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

COLS = "id, title, icon, person_id, days, position, marbles"
MAX_MARBLES = 20


class Chores:
    def __init__(self, db: Database, marbles: Marbles | None = None):
        self.db = db
        self.marbles = marbles
        with db.connect() as conn:
            conn.executescript(SCHEMA)
            # Migrations for databases created by earlier versions
            for table in ("chores", "chore_done"):
                cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
                if "marbles" not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN marbles INTEGER NOT NULL DEFAULT 0")

    def list(self) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(f"SELECT {COLS} FROM chores ORDER BY position, id").fetchall()
        return [dict(r) for r in rows]

    def create(self, title: str, icon: str, person_id: int | None, days: str, marbles: int = 0) -> dict:
        with self.db.connect() as conn:
            pos = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM chores").fetchone()[0]
            cid = conn.execute(
                "INSERT INTO chores(title, icon, person_id, days, position, marbles) VALUES(?, ?, ?, ?, ?, ?)",
                (title, icon, person_id, _norm_days(days), pos, _norm_marbles(marbles)),
            ).lastrowid
            return dict(conn.execute(f"SELECT {COLS} FROM chores WHERE id = ?", (cid,)).fetchone())

    def update(self, cid: int, fields: dict) -> dict | None:
        allowed = {k: v for k, v in fields.items() if k in ("title", "icon", "person_id", "days", "marbles")}
        if "days" in allowed:
            allowed["days"] = _norm_days(allowed["days"])
        if "marbles" in allowed:
            allowed["marbles"] = _norm_marbles(allowed["marbles"])
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
                f"SELECT c.id, c.title, c.icon, c.person_id, c.days, c.position, c.marbles, "
                f"d.person_id AS done_by, d.done_at, d.marbles AS marbles_given FROM chores c "
                f"LEFT JOIN chore_done d ON d.chore_id = c.id AND d.day = ? "
                f"WHERE instr(c.days, ?) > 0 ORDER BY c.position, c.id",
                (key, dow),
            ).fetchall()
        return [dict(r) | {"done": r["done_at"] is not None} for r in rows]

    def set_done(self, cid: int, day: date, done: bool, person_id: int | None) -> dict | None:
        """Check a chore off (or un-check it) for `day`.

        Returns None for an unknown chore, else {"marbles": change} where change lists the jar
        updates: {"person_id", "count"} (count < 0 when marbles were taken back).
        """
        key = day.isoformat()
        changes: list[dict] = []
        with self.db.connect() as conn:
            chore = conn.execute("SELECT title, person_id, marbles FROM chores WHERE id = ?", (cid,)).fetchone()
            if chore is None:
                return None
            prev = conn.execute(
                "SELECT person_id, marbles FROM chore_done WHERE chore_id = ? AND day = ?", (cid, key)
            ).fetchone()
            conn.execute("DELETE FROM chore_done WHERE chore_id = ? AND day = ?", (cid, key))
        note = f"{chore['title']} ({key})"
        # Undo any earlier award for today first (also covers re-assigning an "anyone" chore)
        if prev and prev["marbles"] and prev["person_id"] is not None and self.marbles:
            taken = self.marbles.take_back(prev["person_id"], prev["marbles"], note)
            if taken:
                changes.append({"person_id": prev["person_id"], "count": -taken})
        if done:
            who = chore["person_id"] if chore["person_id"] is not None else person_id
            given = 0
            if chore["marbles"] and who is not None and self.marbles and self.marbles.jar(who) is not None:
                self.marbles.award(who, chore["marbles"], note)
                given = chore["marbles"]
                changes.append({"person_id": who, "count": given})
            with self.db.connect() as conn:
                conn.execute(
                    "INSERT INTO chore_done(chore_id, day, person_id, marbles) VALUES(?, ?, ?, ?)",
                    (cid, key, who, given),
                )
        return {"marbles": changes}


def _norm_marbles(n) -> int:
    n = int(n or 0)
    if not 0 <= n <= MAX_MARBLES:
        raise ValueError(f"A chore can be worth 0 to {MAX_MARBLES} marbles")
    return n


def _norm_days(days: str) -> str:
    d = "".join(sorted({c for c in days if c in "0123456"}))
    if not d:
        raise ValueError("Pick at least one day")
    return d
