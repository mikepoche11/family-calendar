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
    updated     TEXT NOT NULL DEFAULT '',
    color_id    TEXT NOT NULL DEFAULT ''   -- Google Calendar event colour "1".."11"; '' = calendar default
);
CREATE INDEX IF NOT EXISTS events_start ON events(start);

CREATE TABLE IF NOT EXISTS grocery (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL,
    done       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    done_at    TEXT
);

-- Which planned dinner nights put a grocery item on the list. Items with no row here were added by hand.
CREATE TABLE IF NOT EXISTS grocery_meal (
    grocery_id INTEGER NOT NULL REFERENCES grocery(id) ON DELETE CASCADE,
    day        TEXT NOT NULL,            -- local YYYY-MM-DD of the meal_plan night
    PRIMARY KEY (grocery_id, day)
);
CREATE INDEX IF NOT EXISTS grocery_meal_day ON grocery_meal(day);

-- Decorations stuck on the calendar. Only stored here, never sent to Google Calendar.
CREATE TABLE IF NOT EXISTS stickers (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    day      TEXT NOT NULL,              -- YYYY-MM-DD the sticker belongs to
    icon     TEXT NOT NULL,              -- icon name from the app's icon set
    x        REAL NOT NULL DEFAULT 0.5,  -- centre, as a fraction of the day's width (can go past 0..1)
    y        REAL NOT NULL DEFAULT 0.5,  -- centre, as a fraction of the day's height
    size     REAL NOT NULL DEFAULT 0.6,  -- width, as a fraction of the day's shorter side
    rotation REAL NOT NULL DEFAULT 0     -- degrees
);
CREATE INDEX IF NOT EXISTS stickers_day ON stickers(day);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


# Old bright family colours -> their pastel match (pastel theme, 2026-11). Anything else gets mixed with white.
PASTEL_FOR = {
    "#ef4444": "#fca5a5", "#dc2626": "#fca5a5", "#f97316": "#fdba74", "#ea580c": "#fdba74",
    "#f59e0b": "#fde68a", "#eab308": "#fde68a", "#84cc16": "#d9f99d", "#16a34a": "#86efac",
    "#22c55e": "#86efac", "#14b8a6": "#99f6e4", "#0ea5e9": "#7dd3fc", "#2563eb": "#93c5fd",
    "#3b82f6": "#93c5fd", "#7c3aed": "#c4b5fd", "#9333ea": "#c4b5fd", "#c026d3": "#f0abfc",
    "#db2777": "#f9a8d4", "#ec4899": "#f9a8d4", "#64748b": "#cbd5e1", "#94a3b8": "#cbd5e1",
}


def pastel(color: str) -> str:
    c = color.lower()
    if c in PASTEL_FOR:
        return PASTEL_FOR[c]
    try:
        r, g, b = (int(c[i : i + 2], 16) for i in (1, 3, 5))
    except ValueError:
        return color
    if (r + g + b) / 3 >= 170:  # already soft
        return c
    return "#" + "".join(f"{round(v + (255 - v) * 0.55):02x}" for v in (r, g, b))


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
            cols = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
            if "color_id" not in cols:
                # Filled in by the next sync, which also tells the screens to redraw
                conn.execute("ALTER TABLE events ADD COLUMN color_id TEXT NOT NULL DEFAULT ''")

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
                    (name.strip(), (color.strip() or "#cbd5e1"), pos),
                )

    def pastelize_people(self) -> None:
        """One-time switch of saved family colours to the pastel theme."""
        if self.get_meta("pastel_colors"):
            return
        with self.connect() as conn:
            for row in conn.execute("SELECT id, color FROM people").fetchall():
                new = pastel(row["color"])
                if new != row["color"]:
                    conn.execute("UPDATE people SET color = ? WHERE id = ?", (new, row["id"]))
        self.set_meta("pastel_colors", "1")

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
                "SELECT id, summary, description, location, start, end, all_day, person_id, updated, color_id "
                "FROM events WHERE end > ? AND start < ? ORDER BY id",
                (window_start, window_end),
            ).fetchall()
            conn.execute("DELETE FROM events WHERE end > ? AND start < ?", (window_start, window_end))
            conn.executemany(
                "INSERT OR REPLACE INTO events(id, summary, description, location, start, end, all_day, "
                "person_id, recurring, updated, color_id) VALUES(:id, :summary, :description, :location, :start, "
                ":end, :all_day, :person_id, :recurring, :updated, :color_id)",
                events,
            )
            after = conn.execute(
                "SELECT id, summary, description, location, start, end, all_day, person_id, updated, color_id "
                "FROM events WHERE end > ? AND start < ? ORDER BY id",
                (window_start, window_end),
            ).fetchall()
        return [tuple(r) for r in before] != [tuple(r) for r in after]

    def upsert_event(self, event: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO events(id, summary, description, location, start, end, all_day, "
                "person_id, recurring, updated, color_id) VALUES(:id, :summary, :description, :location, :start, "
                ":end, :all_day, :person_id, :recurring, :updated, :color_id)",
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


    # --- grocery list --------------------------------------------------------
    def list_grocery(self) -> list[dict]:
        """Unchecked items first (newest on top), then checked items (most recently checked first)."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, text, done, created_at, done_at FROM grocery "
                "ORDER BY done, CASE WHEN done THEN done_at END DESC, id DESC"
            ).fetchall()
        return [dict(r) | {"done": bool(r["done"])} for r in rows]

    def add_grocery(self, text: str) -> dict:
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM grocery WHERE done = 0 AND lower(text) = lower(?)", (text,)
            ).fetchone()
            if existing:  # already on the list: don't add a duplicate
                gid = existing["id"]
            else:
                gid = conn.execute("INSERT INTO grocery(text) VALUES(?)", (text,)).lastrowid
            row = conn.execute("SELECT id, text, done, created_at, done_at FROM grocery WHERE id = ?", (gid,)).fetchone()
        return dict(row) | {"done": bool(row["done"])}

    def add_grocery_lines(self, lines: list[str | tuple[str, list[str]]]) -> dict:
        """Add many lines; skip any whose item is already on the open list.

        "Onion (2)" counts as already there when "onion" or "Onion (1)" is unchecked on the list.
        A line can be (text, days): the planned dinner nights (YYYY-MM-DD) it is for. Those items are
        remembered so clearing the night takes them off again. A skipped line joins the item already
        on the list only when that item also came from a dinner; hand-added items stay hand-added.
        """
        added, skipped = [], []
        with self.connect() as conn:
            have = {}  # item key -> (grocery id, came from a dinner)
            for r in conn.execute(
                "SELECT id, text, EXISTS(SELECT 1 FROM grocery_meal m WHERE m.grocery_id = g.id) AS planned "
                "FROM grocery g WHERE done = 0 ORDER BY id"
            ):
                have.setdefault(_item_key(r["text"]), (r["id"], bool(r["planned"])))
            for line in lines:
                raw, days = (line, []) if isinstance(line, str) else line
                text = " ".join(raw.split())[:120]
                if not text:
                    continue
                key = _item_key(text)
                if key in have:
                    skipped.append(text)
                    gid, planned = have[key]
                    if not planned:
                        continue
                else:
                    gid = conn.execute("INSERT INTO grocery(text) VALUES(?)", (text,)).lastrowid
                    have[key] = (gid, bool(days))
                    added.append(text)
                conn.executemany(
                    "INSERT OR IGNORE INTO grocery_meal(grocery_id, day) VALUES(?, ?)", [(gid, d) for d in days]
                )
        return {"added": added, "skipped": skipped}

    def forget_dinner_groceries(self, days: list[str]) -> int:
        """A dinner left these nights: drop their links and delete items no other night still needs.

        Checked-off items go too. Hand-added items are never touched. Returns how many items were deleted.
        """
        if not days:
            return 0
        marks = ",".join("?" * len(days))
        with self.connect() as conn:
            ids = [r[0] for r in conn.execute(
                f"SELECT DISTINCT grocery_id FROM grocery_meal WHERE day IN ({marks})", days
            )]
            conn.execute(f"DELETE FROM grocery_meal WHERE day IN ({marks})", days)
            n = 0
            for gid in ids:
                if not conn.execute("SELECT 1 FROM grocery_meal WHERE grocery_id = ?", (gid,)).fetchone():
                    n += conn.execute("DELETE FROM grocery WHERE id = ?", (gid,)).rowcount
        return n

    def update_grocery(self, gid: int, text: str | None = None, done: bool | None = None) -> dict | None:
        with self.connect() as conn:
            if text is not None:
                conn.execute("UPDATE grocery SET text = ? WHERE id = ?", (text, gid))
            if done is not None:
                conn.execute(
                    "UPDATE grocery SET done = ?, done_at = CASE WHEN ? THEN strftime('%Y-%m-%dT%H:%M:%SZ', 'now') END "
                    "WHERE id = ?",
                    (int(done), int(done), gid),
                )
            row = conn.execute("SELECT id, text, done, created_at, done_at FROM grocery WHERE id = ?", (gid,)).fetchone()
        return dict(row) | {"done": bool(row["done"])} if row else None

    def delete_grocery(self, gid: int) -> bool:
        with self.connect() as conn:
            return conn.execute("DELETE FROM grocery WHERE id = ?", (gid,)).rowcount > 0

    def clear_checked_grocery(self) -> int:
        with self.connect() as conn:
            return conn.execute("DELETE FROM grocery WHERE done = 1").rowcount


    # --- calendar stickers ----------------------------------------------------
    STICKER_COLS = "id, day, icon, x, y, size, rotation"

    def list_stickers(self, start: str | None = None, end: str | None = None) -> list[dict]:
        """Stickers on days start <= day < end (YYYY-MM-DD); all of them when no range is given."""
        sql, args = f"SELECT {self.STICKER_COLS} FROM stickers", []
        if start and end:
            sql, args = sql + " WHERE day >= ? AND day < ?", [start, end]
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(sql + " ORDER BY id", args).fetchall()]

    def add_sticker(self, day: str, icon: str, x: float, y: float, size: float, rotation: float) -> dict:
        with self.connect() as conn:
            sid = conn.execute(
                "INSERT INTO stickers(day, icon, x, y, size, rotation) VALUES(?, ?, ?, ?, ?, ?)",
                (day, icon, x, y, size, rotation),
            ).lastrowid
            return dict(conn.execute(f"SELECT {self.STICKER_COLS} FROM stickers WHERE id = ?", (sid,)).fetchone())

    def update_sticker(self, sid: int, **fields) -> dict | None:
        cols = {k: v for k, v in fields.items() if k in ("day", "x", "y", "size", "rotation") and v is not None}
        with self.connect() as conn:
            if cols:
                conn.execute(
                    f"UPDATE stickers SET {', '.join(f'{k} = ?' for k in cols)} WHERE id = ?", (*cols.values(), sid)
                )
            row = conn.execute(f"SELECT {self.STICKER_COLS} FROM stickers WHERE id = ?", (sid,)).fetchone()
        return dict(row) if row else None

    def delete_sticker(self, sid: int) -> bool:
        with self.connect() as conn:
            return conn.execute("DELETE FROM stickers WHERE id = ?", (sid,)).rowcount > 0


def _item_key(text: str) -> str:
    """'Chicken thighs (2 lb)' -> 'chicken thighs': the part before any amount in brackets."""
    return text.split("(")[0].strip().lower()


def _event_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["all_day"] = bool(d["all_day"])
    d["recurring"] = bool(d["recurring"])
    return d
