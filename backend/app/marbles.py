"""Marble jars: each kid has a jar of blue (good) and white (bad) marbles.

- Blue marbles can be spent on rewards (they leave the jar).
- White marbles stay in the jar. "Cancel out" removes whites and blues in pairs, 1 for 1;
  extra whites (or blues) stay.
- Nothing ever resets on its own.

A jar's contents are stored as a string of "b" and "w", bottom of the jar first, so the wall
can draw each marble where it landed. Removing marbles always takes the top-most ones of that
color. Every change is logged with the contents from before it, so the last change can be undone.
"""

from __future__ import annotations

from .db import Database

SCHEMA = """
CREATE TABLE IF NOT EXISTS marble_jars (
    person_id INTEGER PRIMARY KEY REFERENCES people(id) ON DELETE CASCADE,
    contents  TEXT NOT NULL DEFAULT '',
    position  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS marble_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id  INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    action     TEXT NOT NULL,          -- blue | white | spend | cancel
    blue       INTEGER NOT NULL DEFAULT 0,  -- change in blue marbles
    white      INTEGER NOT NULL DEFAULT 0,  -- change in white marbles
    note       TEXT NOT NULL DEFAULT '',
    before     TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS rewards (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    title    TEXT NOT NULL,
    icon     TEXT NOT NULL DEFAULT '',
    cost     INTEGER NOT NULL,
    position INTEGER NOT NULL DEFAULT 0
);
"""

DEFAULT_REWARDS = [
    ("Big ice cream", "🍨", 5),
    ("Small ice cream", "🍦", 3),
    ("Coke", "🥤", 3),
    ("Sprite", "🥤", 3),
    ("Dr Pepper", "🥤", 3),
]

MAX_ADD = 20


class MarbleError(ValueError):
    pass


def remove_top(contents: str, color: str, n: int) -> str:
    """Remove the top-most n marbles of one color."""
    chars = list(contents)
    for i in range(len(chars) - 1, -1, -1):
        if n == 0:
            break
        if chars[i] == color:
            chars[i] = ""
            n -= 1
    return "".join(chars)


class Marbles:
    def __init__(self, db: Database):
        self.db = db
        with db.connect() as conn:
            conn.executescript(SCHEMA)
            if conn.execute("SELECT COUNT(*) FROM rewards").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO rewards(title, icon, cost, position) VALUES(?, ?, ?, ?)",
                    [(t, i, c, n) for n, (t, i, c) in enumerate(DEFAULT_REWARDS)],
                )

    # --- jars ---------------------------------------------------------------------
    def jars(self) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT j.person_id, j.contents, "
                "(SELECT action FROM marble_log l WHERE l.person_id = j.person_id ORDER BY id DESC LIMIT 1) AS last "
                "FROM marble_jars j JOIN people p ON p.id = j.person_id ORDER BY j.position, p.position, p.id"
            ).fetchall()
        return [_jar(r["person_id"], r["contents"], r["last"]) for r in rows]

    def jar(self, pid: int) -> dict | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT contents FROM marble_jars WHERE person_id = ?", (pid,)).fetchone()
            if row is None:
                return None
            last = conn.execute(
                "SELECT action FROM marble_log WHERE person_id = ? ORDER BY id DESC LIMIT 1", (pid,)
            ).fetchone()
        return _jar(pid, row["contents"], last["action"] if last else None)

    def set_jars(self, person_ids: list[int]) -> None:
        """Make sure these people have jars (in this order). Existing marbles are kept."""
        with self.db.connect() as conn:
            for n, pid in enumerate(person_ids):
                conn.execute(
                    "INSERT INTO marble_jars(person_id, position) VALUES(?, ?) "
                    "ON CONFLICT(person_id) DO UPDATE SET position = excluded.position",
                    (pid, n),
                )

    def remove_jar(self, pid: int) -> bool:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM marble_log WHERE person_id = ?", (pid,))
            return conn.execute("DELETE FROM marble_jars WHERE person_id = ?", (pid,)).rowcount > 0

    # --- changes ------------------------------------------------------------------
    def add(self, pid: int, color: str, count: int = 1) -> dict:
        if color not in ("blue", "white"):
            raise MarbleError("Color must be blue or white")
        if not 1 <= count <= MAX_ADD:
            raise MarbleError(f"Add between 1 and {MAX_ADD} marbles at a time")
        c = color[0]
        return self._change(
            pid, color, lambda s: s + c * count,
            blue=count if c == "b" else 0, white=count if c == "w" else 0,
        )

    def spend(self, pid: int, reward_id: int) -> dict:
        reward = self.reward(reward_id)
        if reward is None:
            raise LookupError("No such reward")
        cost = reward["cost"]

        def fn(s: str) -> str:
            if s.count("b") < cost:
                raise MarbleError(f"{reward['title']} costs {cost} blue marbles")
            return remove_top(s, "b", cost)

        return self._change(pid, "spend", fn, blue=-cost, note=reward["title"])

    def cancel(self, pid: int) -> dict:
        jar = self.jar(pid)
        if jar is None:
            raise LookupError("No such jar")
        n = min(jar["blue"], jar["white"])
        if n == 0:
            raise MarbleError("Cancel out needs at least one blue and one white marble")
        return self._change(pid, "cancel", lambda s: remove_top(remove_top(s, "w", n), "b", n), blue=-n, white=-n)

    def undo(self, pid: int) -> dict:
        with self.db.connect() as conn:
            if conn.execute("SELECT 1 FROM marble_jars WHERE person_id = ?", (pid,)).fetchone() is None:
                raise LookupError("No such jar")
            last = conn.execute(
                "SELECT id, before FROM marble_log WHERE person_id = ? ORDER BY id DESC LIMIT 1", (pid,)
            ).fetchone()
            if last is None:
                raise MarbleError("Nothing to undo")
            conn.execute("UPDATE marble_jars SET contents = ? WHERE person_id = ?", (last["before"], pid))
            conn.execute("DELETE FROM marble_log WHERE id = ?", (last["id"],))
        return self.jar(pid)

    def history(self, pid: int, limit: int = 30) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT id, action, blue, white, note, created_at FROM marble_log "
                "WHERE person_id = ? ORDER BY id DESC LIMIT ?",
                (pid, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def _change(self, pid: int, action: str, fn, blue: int = 0, white: int = 0, note: str = "") -> dict:
        with self.db.connect() as conn:
            row = conn.execute("SELECT contents FROM marble_jars WHERE person_id = ?", (pid,)).fetchone()
            if row is None:
                raise LookupError("No such jar")
            before = row["contents"]
            after = fn(before)
            conn.execute("UPDATE marble_jars SET contents = ? WHERE person_id = ?", (after, pid))
            conn.execute(
                "INSERT INTO marble_log(person_id, action, blue, white, note, before) VALUES(?, ?, ?, ?, ?, ?)",
                (pid, action, blue, white, note, before),
            )
        return self.jar(pid)

    # --- rewards ------------------------------------------------------------------
    def rewards(self) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT id, title, icon, cost FROM rewards ORDER BY position, id").fetchall()
        return [dict(r) for r in rows]

    def reward(self, rid: int) -> dict | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT id, title, icon, cost FROM rewards WHERE id = ?", (rid,)).fetchone()
        return dict(row) if row else None

    def create_reward(self, title: str, icon: str, cost: int) -> dict:
        with self.db.connect() as conn:
            pos = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM rewards").fetchone()[0]
            rid = conn.execute(
                "INSERT INTO rewards(title, icon, cost, position) VALUES(?, ?, ?, ?)", (title, icon, cost, pos)
            ).lastrowid
        return self.reward(rid)

    def update_reward(self, rid: int, fields: dict) -> dict | None:
        with self.db.connect() as conn:
            for k, v in fields.items():
                if k in ("title", "icon", "cost"):
                    conn.execute(f"UPDATE rewards SET {k} = ? WHERE id = ?", (v, rid))
        return self.reward(rid)

    def delete_reward(self, rid: int) -> bool:
        with self.db.connect() as conn:
            return conn.execute("DELETE FROM rewards WHERE id = ?", (rid,)).rowcount > 0


def _jar(pid: int, contents: str, last: str | None) -> dict:
    return {
        "person_id": pid,
        "contents": contents,
        "blue": contents.count("b"),
        "white": contents.count("w"),
        "last_action": last,
    }
