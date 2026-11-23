"""Countdowns: "12 days until Christmas". Each one has a name, a date and an icon, and can repeat every year.

`repeat` is one of:
  ''             once, on `day`
  'yearly'       every year on the month and day of `day` (Feb 29 falls on Feb 28 in other years)
  'easter', 'mardi-gras', 'thanksgiving'
                 every year on that holiday, which moves around; `day` is ignored and worked out each year

Only stored in the app, never sent to Google Calendar.
"""

from __future__ import annotations

from datetime import date, timedelta

from .db import Database

SCHEMA = """
CREATE TABLE IF NOT EXISTS countdowns (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT NOT NULL,
    day    TEXT NOT NULL,             -- YYYY-MM-DD
    icon   TEXT NOT NULL DEFAULT '',  -- icon id or emoji, as the icon picker saves it
    repeat TEXT NOT NULL DEFAULT ''
);
"""

MOVING = ("easter", "mardi-gras", "thanksgiving")
REPEATS = ("", "yearly", *MOVING)
COLS = "id, name, day, icon, repeat"

# "Add holidays" button: (name, icon, month-day or moving rule)
HOLIDAYS = [
    ("Christmas", "xmas-tree", "12-25"),
    ("Mardi Gras", "mardi-mask", "mardi-gras"),
    ("Valentine's Day", "valentine-heart", "02-14"),
    ("Easter", "easter-bunny", "easter"),
    ("July 4th", "july4-firework", "07-04"),
    ("Halloween", "halloween-pumpkin", "10-31"),
    ("Thanksgiving", "thanks-turkey", "thanksgiving"),
]


def easter(year: int) -> date:
    """Western Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def on_year(repeat: str, day: date, year: int) -> date:
    """The countdown's date in a given year."""
    if repeat == "easter":
        return easter(year)
    if repeat == "mardi-gras":
        return easter(year) - timedelta(days=47)
    if repeat == "thanksgiving":
        first = date(year, 11, 1)
        return first + timedelta(days=(3 - first.weekday()) % 7 + 21)  # 4th Thursday
    if day.month == 2 and day.day == 29:
        try:
            return date(year, 2, 29)
        except ValueError:
            return date(year, 2, 28)
    return day.replace(year=year)


def next_date(repeat: str, day: date, today: date) -> date:
    """Next time it happens, today included. A one-off keeps its own date, even once it has passed."""
    if not repeat:
        return day
    d = on_year(repeat, day, today.year)
    return d if d >= today else on_year(repeat, day, today.year + 1)


class Countdowns:
    def __init__(self, db: Database):
        self.db = db
        with db.connect() as conn:
            conn.executescript(SCHEMA)

    def _row(self, conn, cid: int) -> dict | None:
        r = conn.execute(f"SELECT {COLS} FROM countdowns WHERE id = ?", (cid,)).fetchone()
        return dict(r) if r else None

    @staticmethod
    def _with_days(row: dict, today: date) -> dict:
        nxt = next_date(row["repeat"], date.fromisoformat(row["day"]), today)
        return row | {"next": nxt.isoformat(), "days": (nxt - today).days}

    def list(self, today: date) -> list[dict]:
        """Soonest first; one-offs that have passed go last, most recent first."""
        with self.db.connect() as conn:
            rows = [dict(r) for r in conn.execute(f"SELECT {COLS} FROM countdowns")]
        out = [self._with_days(r, today) for r in rows]
        out.sort(key=lambda r: (r["days"] < 0, abs(r["days"]), r["name"].lower()))
        return out

    def get(self, cid: int, today: date) -> dict | None:
        with self.db.connect() as conn:
            row = self._row(conn, cid)
        return self._with_days(row, today) if row else None

    def create(self, name: str, day: str, icon: str, repeat: str, today: date) -> dict:
        with self.db.connect() as conn:
            cid = conn.execute(
                "INSERT INTO countdowns(name, day, icon, repeat) VALUES(?, ?, ?, ?)", (name, day, icon, repeat)
            ).lastrowid
        return self.get(cid, today)

    def update(self, cid: int, fields: dict, today: date) -> dict | None:
        cols = {k: v for k, v in fields.items() if k in ("name", "day", "icon", "repeat") and v is not None}
        with self.db.connect() as conn:
            if not self._row(conn, cid):
                return None
            if cols:
                conn.execute(
                    f"UPDATE countdowns SET {', '.join(f'{k} = ?' for k in cols)} WHERE id = ?", (*cols.values(), cid)
                )
        return self.get(cid, today)

    def delete(self, cid: int) -> bool:
        with self.db.connect() as conn:
            return conn.execute("DELETE FROM countdowns WHERE id = ?", (cid,)).rowcount > 0

    def add_holidays(self, today: date) -> int:
        """Add the usual holidays, skipping any already on the list by name. Returns how many were added."""
        with self.db.connect() as conn:
            have = {r[0].strip().lower() for r in conn.execute("SELECT name FROM countdowns")}
            added = 0
            for name, icon, when in HOLIDAYS:
                if name.lower() in have:
                    continue
                if when in MOVING:
                    repeat, day = when, next_date(when, today, today)
                else:
                    repeat = "yearly"
                    day = next_date(repeat, date.fromisoformat(f"{today.year}-{when}"), today)
                conn.execute(
                    "INSERT INTO countdowns(name, day, icon, repeat) VALUES(?, ?, ?, ?)",
                    (name, day.isoformat(), icon, repeat),
                )
                added += 1
        return added
