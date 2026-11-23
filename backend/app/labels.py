"""Colours for Google Calendar's event labels.

Google's newer "event labels" (the named colours in the Google Calendar app) come through the API only as
an `eventLabelId` on each event; the label's name and colour do not, and the service account can't read the
calendar settings that hold them. So the family picks a colour for each label once, in Settings, and it is
saved in meta key `label_colors` as {label id: "#rrggbb"}.

An event's own classic colour (colorId) still wins over its label's colour.
"""

from __future__ import annotations

import json
import re

from .db import Database

KEY = "label_colors"
HINTED = "label_hints_done"  # labels already given a first guess, so a colour cleared on purpose stays cleared
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# First guess for labels nobody has coloured yet, from words in their events' titles. Matches the colours the
# Poche Family calendar showed in the Google app on Mike's phone (2026-11-22). Only used until a colour is picked.
HINTS = [
    ("church", "#7986cb"),         # lavender
    ("always", "#e67c73"),         # flamingo pink
    ("no school", "#d16d8f"),      # raspberry
    ("early dismiss", "#d16d8f"),
    ("nails", "#26a69a"),          # eucalyptus teal
    ("trash", "#a1887f"),          # cocoa
    ("larry pool", "#a79b8e"),     # birch
    ("pick up cheer", "#b39ddb"),  # wisteria
    ("mike $$", "#7cb342"),        # avocado
    ("kenia", "#c0ca33"),          # citron
]


class EventLabels:
    def __init__(self, db: Database):
        self.db = db

    def colors(self) -> dict[str, str]:
        try:
            data = json.loads(self.db.get_meta(KEY) or "{}")
        except ValueError:
            return {}
        return {k: v for k, v in data.items() if isinstance(v, str) and HEX.match(v)} if isinstance(data, dict) else {}

    def set_color(self, label_id: str, color: str | None) -> dict[str, str]:
        if color is not None and not HEX.match(color):
            raise ValueError("Colour must look like #a1b2c3")
        data = self.colors()
        if color:
            data[label_id] = color.lower()
        else:
            data.pop(label_id, None)
        self.db.set_meta(KEY, json.dumps(data))
        return data

    def list(self) -> list[dict]:
        """Every label seen on synced events, busiest first, with a few example titles and its colour."""
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT label_id, summary, COUNT(*) AS n FROM events WHERE label_id != '' "
                "GROUP BY label_id, summary ORDER BY n DESC"
            ).fetchall()
            plain = {
                r[0]
                for r in conn.execute("SELECT DISTINCT label_id FROM events WHERE label_id != '' AND color_id = ''")
            }
        labels: dict[str, dict] = {}
        for r in rows:
            lab = labels.setdefault(r["label_id"], {"label_id": r["label_id"], "count": 0, "examples": []})
            lab["count"] += r["n"]
            if len(lab["examples"]) < 4:
                lab["examples"].append(r["summary"])
        colors = self.colors()
        out = []
        for lab in labels.values():
            lab["color"] = colors.get(lab["label_id"], "")
            # Labels whose events all carry a classic colour already look right; they're listed last
            lab["needs_color"] = lab["label_id"] in plain
            out.append(lab)
        out.sort(key=lambda l: (not l["needs_color"], -l["count"]))
        return out

    def apply_hints(self) -> bool:
        """Give uncoloured labels a first colour from HINTS. Returns True when any were set."""
        colors = self.colors()
        try:
            done = set(json.loads(self.db.get_meta(HINTED) or "[]"))
        except ValueError:
            done = set()
        changed = False
        for lab in self.list():
            if lab["label_id"] in colors or lab["label_id"] in done:
                continue
            done.add(lab["label_id"])
            titles = " | ".join(lab["examples"]).lower()
            hit = next((c for word, c in HINTS if word in titles), None)
            if hit:
                colors[lab["label_id"]] = hit
                changed = True
        self.db.set_meta(HINTED, json.dumps(sorted(done)))
        if changed:
            self.db.set_meta(KEY, json.dumps(colors))
        return changed
