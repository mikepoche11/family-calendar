"""Show night: which kid picks the TV show tonight. Takes turns by calendar date, changing over at midnight.

Saved in meta key `show_night` as {"order": [person ids], "anchor": "YYYY-MM-DD", "start": i}: on the anchor
day order[start] picks, and each day after that it moves one along the list. "Swap tonight" re-anchors on today
with the next kid, so a skipped night just shifts the turns from then on.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from .db import Database

KEY = "show_night"
# Mike asked (2026-11-22): Aaron and Jordyn take turns, Aaron picks first on 2026-11-22
DEFAULT_NAMES = ("Aaron", "Jordyn")
DEFAULT_ANCHOR = "2026-11-22"


class ShowNight:
    def __init__(self, db: Database):
        self.db = db

    def _load(self) -> dict | None:
        try:
            data = json.loads(self.db.get_meta(KEY) or "null")
        except ValueError:
            return None
        if not isinstance(data, dict) or not isinstance(data.get("order"), list):
            return None
        try:
            date.fromisoformat(data.get("anchor", ""))
        except (TypeError, ValueError):
            return None
        return data

    def _save(self, order: list[int], anchor: date, start: int) -> None:
        self.db.set_meta(KEY, json.dumps({"order": order, "anchor": anchor.isoformat(), "start": start}))

    def _state(self) -> dict:
        """Saved rotation with removed people dropped; the default (Aaron, Jordyn) until one is saved."""
        ids = {p["id"] for p in self.db.list_people()}
        data = self._load()
        if data is None:
            by_name = {p["name"].strip().lower(): p["id"] for p in self.db.list_people()}
            order = [by_name[n.lower()] for n in DEFAULT_NAMES if n.lower() in by_name]
            return {"order": order, "anchor": DEFAULT_ANCHOR, "start": 0}
        old = data["order"]
        start = int(data.get("start", 0))
        order = [i for i in old if i in ids]
        if order != old and old:
            # Keep the same kid on the anchor day if they're still in the list
            keep = old[start % len(old)]
            start = order.index(keep) if keep in order else 0
        return {"order": order, "anchor": data["anchor"], "start": start}

    @staticmethod
    def _index(state: dict, day: date) -> int | None:
        n = len(state["order"])
        if not n:
            return None
        return (state["start"] + (day - date.fromisoformat(state["anchor"])).days) % n

    def get(self, today: date) -> dict:
        s = self._state()
        i = self._index(s, today)
        j = self._index(s, today + timedelta(days=1))
        return {
            "date": today.isoformat(),
            "order": s["order"],
            "tonight": None if i is None else s["order"][i],
            "tomorrow": None if j is None else s["order"][j],
        }

    def set_order(self, order: list[int], today: date) -> dict:
        """New list of kids. Whoever picks tonight keeps tonight if they're still in it, else the first kid."""
        tonight = self.get(today)["tonight"]
        order = list(dict.fromkeys(order))
        start = order.index(tonight) if tonight in order else 0
        self._save(order, today, start)
        return self.get(today)

    def swap(self, today: date) -> dict:
        """Give tonight to the next kid; the turns carry on from them."""
        s = self._state()
        i = self._index(s, today)
        if i is None:
            return self.get(today)
        self._save(s["order"], today, (i + 1) % len(s["order"]))
        return self.get(today)
