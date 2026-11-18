"""Turning Google Calendar events into rows, and deciding whose event it is.

The family shares one Google calendar ("Poche Family"), so the owner of an event
is read from its title:

    "Mike: Dentist"      -> Mike
    "[Mike] Dentist"     -> Mike
    "Mike & Ava: Recital"-> Mike (first match wins)

Events with no name match belong to nobody and show in the neutral family colour.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


def match_person(summary: str, people: list[dict]) -> int | None:
    title = summary.strip().lower()
    best: tuple[int, int] | None = None  # (position in title, person id)
    for person in people:
        name = person["name"].strip().lower()
        if not name:
            continue
        patterns = [
            rf"^{re.escape(name)}\s*[:\-&,]",  # "Mike: ..." / "Mike - ..." / "Mike & Ava"
            rf"\[{re.escape(name)}\]",  # "[Mike] ..."
            rf"^[^:]*\b{re.escape(name)}\b[^:]*:",  # "Ava & Mike: ..." (names before the colon)
        ]
        for pat in patterns:
            m = re.search(pat, title)
            if m:
                pos = title.find(name, m.start())
                if best is None or pos < best[0]:
                    best = (pos, person["id"])
                break
    return best[1] if best else None


def to_utc_iso(value: str) -> str:
    """Normalise an RFC 3339 datetime to UTC 'YYYY-MM-DDTHH:MM:SSZ'."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_google(item: dict, people: list[dict]) -> dict | None:
    """Google API event resource -> events table row. Returns None for cancelled events."""
    if item.get("status") == "cancelled":
        return None
    start, end = item.get("start", {}), item.get("end", {})
    all_day = "date" in start
    if all_day:
        s, e = start["date"], end.get("date", start["date"])
    else:
        s, e = to_utc_iso(start["dateTime"]), to_utc_iso(end.get("dateTime", start["dateTime"]))
    summary = item.get("summary") or "(no title)"
    return {
        "id": item["id"],
        "summary": summary,
        "description": item.get("description", ""),
        "location": item.get("location", ""),
        "start": s,
        "end": e,
        "all_day": int(all_day),
        "person_id": match_person(summary, people),
        "recurring": int(bool(item.get("recurringEventId"))),
        "updated": item.get("updated", ""),
    }


def to_google(payload: dict, tz: str) -> dict:
    """API input -> Google API event body."""
    body: dict = {"summary": payload["summary"]}
    if payload.get("description"):
        body["description"] = payload["description"]
    if payload.get("location"):
        body["location"] = payload["location"]
    if payload.get("all_day"):
        body["start"] = {"date": payload["start"][:10]}
        body["end"] = {"date": payload["end"][:10]}
    else:
        body["start"] = {"dateTime": payload["start"], "timeZone": tz}
        body["end"] = {"dateTime": payload["end"], "timeZone": tz}
    return body


def titled_for(summary: str, person: dict | None, people: list[dict]) -> str:
    """Prefix the title with 'Name: ' so the owner survives the round trip through Google."""
    if person is None or match_person(summary, people) == person["id"]:
        return summary
    return f"{person['name']}: {summary}"
