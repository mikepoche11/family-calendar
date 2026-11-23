"""Morning and bedtime routines: a short checklist per kid that starts fresh every day.

Each step belongs to one routine ("morning" or "bedtime") and one person, repeats on chosen weekdays
("days": digits 0-6, Monday = 0) and can be worth blue marbles, like chores. Finishing every step of a
routine can also earn a bonus (set per routine). Unchecking a step takes back what it gave, and the
bonus too if the routine is no longer finished.

The times each routine shows on the wall are saved in meta key `routines`.
"""

from __future__ import annotations

import json
import re
from datetime import date

from .db import Database
from .marbles import Marbles

KINDS = ("morning", "bedtime")
LABEL = {"morning": "Morning routine", "bedtime": "Bedtime routine"}
MAX_MARBLES = 20
META_KEY = "routines"

SCHEMA = """
CREATE TABLE IF NOT EXISTS routine_steps (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    kind      TEXT NOT NULL,                                     -- morning | bedtime
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    title     TEXT NOT NULL,
    icon      TEXT NOT NULL DEFAULT '',
    days      TEXT NOT NULL DEFAULT '0123456',
    position  INTEGER NOT NULL DEFAULT 0,
    marbles   INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS routine_done (
    step_id INTEGER NOT NULL REFERENCES routine_steps(id) ON DELETE CASCADE,
    day     TEXT NOT NULL,                                       -- local YYYY-MM-DD
    done_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    marbles INTEGER NOT NULL DEFAULT 0,                          -- blue marbles actually given
    PRIMARY KEY (step_id, day)
);
CREATE TABLE IF NOT EXISTS routine_bonus (
    kind      TEXT NOT NULL,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    day       TEXT NOT NULL,
    marbles   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (kind, person_id, day)
);
"""

DEFAULT_SETTINGS = {
    "morning": {"start": "06:00", "end": "09:00", "bonus": 0},
    "bedtime": {"start": "19:00", "end": "21:00", "bonus": 0},
    "auto_show": True,  # switch the wall to the routine while it's on (when nobody is using the screen)
}

# Starter steps for each chosen kid: (routine, title, icon, days)
STARTER = [
    ("morning", "Get dressed", "👕", "0123456"),
    ("morning", "Eat breakfast", "🥣", "0123456"),
    ("morning", "Brush teeth", "🪥", "0123456"),
    ("morning", "Brush hair", "🪮", "0123456"),
    ("morning", "Shoes on", "👟", "0123456"),
    ("morning", "Backpack ready", "🎒", "01234"),
    ("bedtime", "Bath or shower", "🛁", "0123456"),
    ("bedtime", "Pajamas on", "🌙", "0123456"),
    ("bedtime", "Brush teeth", "🪥", "0123456"),
    ("bedtime", "Clothes in the hamper", "🧺", "0123456"),
    ("bedtime", "Read a book", "📖", "0123456"),
    ("bedtime", "Lights out", "🛏️", "0123456"),
]

COLS = "id, kind, person_id, title, icon, days, position, marbles"
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class Routines:
    def __init__(self, db: Database, marbles: Marbles | None = None):
        self.db = db
        self.marbles = marbles
        with db.connect() as conn:
            conn.executescript(SCHEMA)

    # --- settings ---------------------------------------------------------------------
    def settings(self) -> dict:
        out = json.loads(json.dumps(DEFAULT_SETTINGS))
        try:
            saved = json.loads(self.db.get_meta(META_KEY) or "{}")
        except ValueError:
            saved = {}
        if isinstance(saved, dict):
            for kind in KINDS:
                if isinstance(saved.get(kind), dict):
                    out[kind].update({k: v for k, v in saved[kind].items() if k in out[kind]})
            if isinstance(saved.get("auto_show"), bool):
                out["auto_show"] = saved["auto_show"]
        return out

    def set_settings(self, fields: dict) -> dict:
        cur = self.settings()
        for kind in KINDS:
            for k, v in (fields.get(kind) or {}).items():
                if k in ("start", "end"):
                    if not isinstance(v, str) or not TIME.match(v):
                        raise ValueError("Times look like 06:30")
                    cur[kind][k] = v
                elif k == "bonus":
                    cur[kind][k] = _norm_marbles(v)
            if cur[kind]["start"] >= cur[kind]["end"]:
                raise ValueError(f"The {LABEL[kind].lower()} has to end after it starts")
        if "auto_show" in fields:
            cur["auto_show"] = bool(fields["auto_show"])
        m, b = cur["morning"], cur["bedtime"]
        if m["start"] < b["end"] and b["start"] < m["end"]:
            raise ValueError("Morning and bedtime times overlap")
        self.db.set_meta(META_KEY, json.dumps(cur))
        return cur

    # --- steps ------------------------------------------------------------------------
    def list(self) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(f"SELECT {COLS} FROM routine_steps ORDER BY kind, person_id, position, id").fetchall()
        return [dict(r) for r in rows]

    def create(self, kind: str, person_id: int, title: str, icon: str = "", days: str = "0123456", marbles: int = 0) -> dict:
        kind = _norm_kind(kind)
        with self.db.connect() as conn:
            pos = conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM routine_steps WHERE kind = ? AND person_id = ?",
                (kind, person_id),
            ).fetchone()[0]
            sid = conn.execute(
                "INSERT INTO routine_steps(kind, person_id, title, icon, days, position, marbles) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (kind, person_id, title, icon, _norm_days(days), pos, _norm_marbles(marbles)),
            ).lastrowid
            return dict(conn.execute(f"SELECT {COLS} FROM routine_steps WHERE id = ?", (sid,)).fetchone())

    def update(self, sid: int, fields: dict) -> dict | None:
        allowed = {k: v for k, v in fields.items() if k in ("title", "icon", "days", "marbles")}
        if "days" in allowed:
            allowed["days"] = _norm_days(allowed["days"])
        if "marbles" in allowed:
            allowed["marbles"] = _norm_marbles(allowed["marbles"])
        with self.db.connect() as conn:
            for k, v in allowed.items():
                conn.execute(f"UPDATE routine_steps SET {k} = ? WHERE id = ?", (v, sid))
            row = conn.execute(f"SELECT {COLS} FROM routine_steps WHERE id = ?", (sid,)).fetchone()
        return dict(row) if row else None

    def move(self, sid: int, delta: int) -> bool:
        """Move a step up (-1) or down (+1) within its kid's routine."""
        with self.db.connect() as conn:
            row = conn.execute("SELECT kind, person_id FROM routine_steps WHERE id = ?", (sid,)).fetchone()
            if row is None:
                return False
            ids = [
                r[0]
                for r in conn.execute(
                    "SELECT id FROM routine_steps WHERE kind = ? AND person_id = ? ORDER BY position, id",
                    (row["kind"], row["person_id"]),
                )
            ]
            i = ids.index(sid)
            j = max(0, min(len(ids) - 1, i + delta))
            ids.insert(j, ids.pop(i))
            conn.executemany("UPDATE routine_steps SET position = ? WHERE id = ?", [(n, x) for n, x in enumerate(ids)])
        return True

    def delete(self, sid: int) -> bool:
        with self.db.connect() as conn:
            return conn.execute("DELETE FROM routine_steps WHERE id = ?", (sid,)).rowcount > 0

    def copy(self, from_pid: int, to_pid: int, kind: str) -> int:
        """Copy one kid's routine steps to another kid (added after their own steps)."""
        kind = _norm_kind(kind)
        steps = [s for s in self.list() if s["kind"] == kind and s["person_id"] == from_pid]
        for s in steps:
            self.create(kind, to_pid, s["title"], s["icon"], s["days"], s["marbles"])
        return len(steps)

    def add_starter(self, kid_ids: list[int]) -> int:
        n = 0
        for pid in kid_ids:
            for kind, title, icon, days in STARTER:
                self.create(kind, pid, title, icon, days)
                n += 1
        return n

    # --- a day ------------------------------------------------------------------------
    def for_day(self, day: date) -> dict:
        """Steps scheduled on `day` with done flags, plus the bonuses already given that day."""
        dow = str(day.weekday())
        key = day.isoformat()
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT s.id, s.kind, s.person_id, s.title, s.icon, s.days, s.position, s.marbles, "
                "d.done_at, d.marbles AS marbles_given FROM routine_steps s "
                "LEFT JOIN routine_done d ON d.step_id = s.id AND d.day = ? "
                "WHERE instr(s.days, ?) > 0 ORDER BY s.person_id, s.position, s.id",
                (key, dow),
            ).fetchall()
            bonus = conn.execute("SELECT kind, person_id, marbles FROM routine_bonus WHERE day = ?", (key,)).fetchall()
        return {
            "steps": [dict(r) | {"done": r["done_at"] is not None} for r in rows],
            "bonus": [dict(b) for b in bonus],
        }

    def set_done(self, sid: int, day: date, done: bool) -> dict | None:
        """Check a step off (or uncheck it). Returns None for an unknown step, else
        {"marbles": [{"person_id", "count"}...], "finished": bool} (count < 0 when taken back)."""
        key = day.isoformat()
        with self.db.connect() as conn:
            step = conn.execute(
                "SELECT kind, person_id, title, marbles FROM routine_steps WHERE id = ?", (sid,)
            ).fetchone()
            if step is None:
                return None
            prev = conn.execute(
                "SELECT marbles FROM routine_done WHERE step_id = ? AND day = ?", (sid, key)
            ).fetchone()
            conn.execute("DELETE FROM routine_done WHERE step_id = ? AND day = ?", (sid, key))
        kind, pid = step["kind"], step["person_id"]
        has_jar = self.marbles is not None and self.marbles.jar(pid) is not None
        note = f"{LABEL[kind]}: {step['title']} ({key})"
        # The bonus came last, so it goes back first (keeps the jar's history tidy)
        _, bonus_change = self._settle_bonus(kind, pid, day, has_jar)
        total = 0
        if prev and prev["marbles"] and has_jar:
            total -= self.marbles.take_back(pid, prev["marbles"], note)
        given = 0
        if done:
            if step["marbles"] and has_jar:
                self.marbles.award(pid, step["marbles"], note)
                given = step["marbles"]
                total += given
            with self.db.connect() as conn:
                conn.execute(
                    "INSERT INTO routine_done(step_id, day, marbles) VALUES(?, ?, ?)", (sid, key, given)
                )
        finished, change = self._settle_bonus(kind, pid, day, has_jar)
        bonus_change += change
        net = total + bonus_change
        changes = [{"person_id": pid, "count": net}] if net else []
        return {"marbles": changes, "finished": finished, "bonus": max(change, 0)}

    def _settle_bonus(self, kind: str, pid: int, day: date, has_jar: bool) -> tuple[bool, int]:
        """Give the finish bonus when every step is done, take it back when one is unchecked."""
        key = day.isoformat()
        steps = [s for s in self.for_day(day)["steps"] if s["kind"] == kind and s["person_id"] == pid]
        finished = bool(steps) and all(s["done"] for s in steps)
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT marbles FROM routine_bonus WHERE kind = ? AND person_id = ? AND day = ?", (kind, pid, key)
            ).fetchone()
        note = f"{LABEL[kind]} all done ({key})"
        if finished and row is None:
            bonus = self.settings()[kind]["bonus"] if has_jar else 0
            if bonus:
                self.marbles.award(pid, bonus, note)
            with self.db.connect() as conn:
                conn.execute(
                    "INSERT INTO routine_bonus(kind, person_id, day, marbles) VALUES(?, ?, ?, ?)", (kind, pid, key, bonus)
                )
            return True, bonus
        if not finished and row is not None:
            taken = self.marbles.take_back(pid, row["marbles"], note) if row["marbles"] and has_jar else 0
            with self.db.connect() as conn:
                conn.execute(
                    "DELETE FROM routine_bonus WHERE kind = ? AND person_id = ? AND day = ?", (kind, pid, key)
                )
            return False, -taken
        return finished, 0


def _norm_kind(kind: str) -> str:
    if kind not in KINDS:
        raise ValueError("Routine must be morning or bedtime")
    return kind


def _norm_marbles(n) -> int:
    n = int(n or 0)
    if not 0 <= n <= MAX_MARBLES:
        raise ValueError(f"Pick 0 to {MAX_MARBLES} marbles")
    return n


def _norm_days(days: str) -> str:
    d = "".join(sorted({c for c in days if c in "0123456"}))
    if not d:
        raise ValueError("Pick at least one day")
    return d
