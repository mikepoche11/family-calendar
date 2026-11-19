"""Meal planning: a box of the family's meals and a dinner plan, one meal per night.

A meal has a name, an icon, its ingredients (one grocery line each) and an optional recipe link.
The plan maps a local date (YYYY-MM-DD) to a meal. Weeks start on Monday, like chores.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta

from .db import Database

SCHEMA = """
CREATE TABLE IF NOT EXISTS meals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    icon        TEXT NOT NULL DEFAULT '',
    ingredients TEXT NOT NULL DEFAULT '[]',   -- JSON list of grocery lines
    url         TEXT NOT NULL DEFAULT '',     -- recipe link
    image       TEXT NOT NULL DEFAULT '',     -- photo URL (ideas from TheMealDB)
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS meal_plan (
    day     TEXT PRIMARY KEY,                                        -- local YYYY-MM-DD
    meal_id INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE
);
"""

# Family-friendly starters (south Louisiana leaning). Everything is editable in the app.
STARTER = [
    ("Tacos", "🌮", ["Ground beef (1 lb)", "Taco seasoning", "Taco shells", "Shredded cheese", "Lettuce",
                     "Tomatoes", "Sour cream", "Salsa"]),
    ("Spaghetti and meatballs", "🍝", ["Spaghetti", "Pasta sauce", "Frozen meatballs", "Parmesan cheese",
                                       "Garlic bread"]),
    ("Red beans and rice", "🫘", ["Red kidney beans (1 lb dry)", "Smoked sausage", "Onion", "Bell pepper",
                                  "Celery", "Garlic", "Rice", "Cajun seasoning"]),
    ("Chicken and sausage jambalaya", "🥘", ["Chicken thighs (2 lb)", "Andouille sausage", "Rice", "Onion",
                                             "Bell pepper", "Celery", "Chicken broth", "Diced tomatoes",
                                             "Cajun seasoning"]),
    ("Chicken and sausage gumbo", "🍲", ["Chicken thighs (2 lb)", "Andouille sausage", "Flour", "Vegetable oil",
                                         "Onion", "Bell pepper", "Celery", "Chicken broth", "Rice",
                                         "Green onions"]),
    ("Breakfast for dinner", "🥞", ["Pancake mix", "Eggs", "Bacon", "Maple syrup", "Milk"]),
    ("Grilled cheese and tomato soup", "🥪", ["Bread", "Sliced cheese", "Butter", "Tomato soup"]),
    ("Pizza night", "🍕", ["Pizza dough", "Pizza sauce", "Mozzarella", "Pepperoni"]),
    ("Chicken tenders and fries", "🍗", ["Chicken tenders", "Breadcrumbs", "Eggs", "Frozen fries",
                                         "Honey mustard"]),
    ("Leftovers", "🥡", []),
    ("Eating out", "🍔", []),
]

COLS = "id, name, icon, ingredients, url, image"


def _row(r) -> dict:
    d = dict(r)
    d["ingredients"] = json.loads(d["ingredients"] or "[]")
    return d


def clean_lines(lines: list[str]) -> list[str]:
    """Trim, drop blanks and repeated lines (case-insensitive), keep order."""
    out, seen = [], set()
    for line in lines:
        s = " ".join(str(line).split())[:120]
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


class Meals:
    def __init__(self, db: Database):
        self.db = db
        with db.connect() as conn:
            conn.executescript(SCHEMA)

    # --- meal box -----------------------------------------------------------
    def list(self) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(f"SELECT {COLS} FROM meals ORDER BY name COLLATE NOCASE").fetchall()
        return [_row(r) for r in rows]

    def get(self, mid: int) -> dict | None:
        with self.db.connect() as conn:
            r = conn.execute(f"SELECT {COLS} FROM meals WHERE id = ?", (mid,)).fetchone()
        return _row(r) if r else None

    def create(self, name: str, icon: str = "", ingredients: list[str] | None = None, url: str = "",
               image: str = "") -> dict:
        """Add a meal. A meal with the same name (any case) is returned as is instead of duplicated."""
        with self.db.connect() as conn:
            existing = conn.execute("SELECT id FROM meals WHERE name = ?", (name,)).fetchone()
            if existing:
                mid = existing["id"]
            else:
                mid = conn.execute(
                    "INSERT INTO meals(name, icon, ingredients, url, image) VALUES(?, ?, ?, ?, ?)",
                    (name, icon, json.dumps(clean_lines(ingredients or [])), url, image),
                ).lastrowid
        return self.get(mid)

    def update(self, mid: int, fields: dict) -> dict | None:
        allowed = {k: v for k, v in fields.items() if k in ("name", "icon", "ingredients", "url", "image")}
        if "ingredients" in allowed:
            allowed["ingredients"] = json.dumps(clean_lines(allowed["ingredients"]))
        with self.db.connect() as conn:
            for k, v in allowed.items():
                conn.execute(f"UPDATE meals SET {k} = ? WHERE id = ?", (v, mid))
        return self.get(mid)

    def delete(self, mid: int) -> bool:
        with self.db.connect() as conn:
            return conn.execute("DELETE FROM meals WHERE id = ?", (mid,)).rowcount > 0

    def add_starter(self) -> int:
        before = len(self.list())
        for name, icon, ingredients in STARTER:
            self.create(name, icon, ingredients)
        return len(self.list()) - before

    # --- plan ---------------------------------------------------------------
    def week(self, start: date) -> list[dict]:
        """Seven days from `start`, each {date, meal or None}."""
        days = [start + timedelta(days=i) for i in range(7)]
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT p.day, m.id, m.name, m.icon, m.ingredients, m.url, m.image FROM meal_plan p "
                f"JOIN meals m ON m.id = p.meal_id WHERE p.day >= ? AND p.day <= ?",
                (days[0].isoformat(), days[-1].isoformat()),
            ).fetchall()
        by_day = {r["day"]: _row({k: r[k] for k in r.keys() if k != "day"}) for r in rows}
        return [{"date": d.isoformat(), "meal": by_day.get(d.isoformat())} for d in days]

    def set_day(self, day: date, meal_id: int | None) -> bool:
        with self.db.connect() as conn:
            if meal_id is None:
                conn.execute("DELETE FROM meal_plan WHERE day = ?", (day.isoformat(),))
                return True
            if not conn.execute("SELECT 1 FROM meals WHERE id = ?", (meal_id,)).fetchone():
                return False
            conn.execute(
                "INSERT INTO meal_plan(day, meal_id) VALUES(?, ?) "
                "ON CONFLICT(day) DO UPDATE SET meal_id = excluded.meal_id",
                (day.isoformat(), meal_id),
            )
        return True

    def fill_week(self, start: date, rng: random.Random | None = None) -> int:
        """Put a different saved meal on each empty night, avoiding meals already planned that week.

        "Leftovers" and "Eating out" are left for people to place on purpose.
        """
        rng = rng or random.Random()
        week = self.week(start)
        used = {d["meal"]["id"] for d in week if d["meal"]}
        pool = [m for m in self.list() if m["id"] not in used and m["ingredients"]]
        rng.shuffle(pool)
        n = 0
        for d in week:
            if d["meal"] is None and pool:
                self.set_day(date.fromisoformat(d["date"]), pool.pop()["id"])
                n += 1
        return n
