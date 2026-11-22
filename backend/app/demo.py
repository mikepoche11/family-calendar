"""Sample events for demo mode (no Google credentials), so the wall UI can be built and tested."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .events import match_person, to_utc_iso

SAMPLES = [
    # (day offset, start hh:mm or None for all-day, duration minutes, title, Google colour id)
    (0, "07:30", 30, "Family: School drop-off", "7"),
    (0, "16:00", 90, "Ava: Soccer practice", "2"),
    (0, "18:30", 60, "Mike: Gym", "9"),
    (1, None, 0, "Trash day", "8"),
    (1, "09:00", 60, "Mom: Dentist", "4"),
    (2, "17:30", 60, "Ava: Piano lesson", "3"),
    (3, "19:00", 120, "Date night", "11"),
    (5, None, 0, "Grandma visiting", "5"),
    (6, "10:00", 120, "Ava: Birthday party at the park", "6"),
    (9, "08:00", 480, "Mike: Work trip", "1"),
    (14, None, 0, "No school", "10"),
]


def demo_events(people: list[dict], tz: str) -> list[dict]:
    zone = ZoneInfo(tz)
    today = date.today()
    rows = []
    for i, (offset, start, minutes, title, color_id) in enumerate(SAMPLES):
        day = today + timedelta(days=offset)
        if start is None:
            s, e, all_day = day.isoformat(), (day + timedelta(days=1)).isoformat(), 1
        else:
            hh, mm = map(int, start.split(":"))
            dt = datetime.combine(day, time(hh, mm), tzinfo=zone)
            s, e, all_day = to_utc_iso(dt.isoformat()), to_utc_iso((dt + timedelta(minutes=minutes)).isoformat()), 0
        rows.append({
            "id": f"demo{i}",
            "summary": title,
            "description": "",
            "location": "",
            "start": s,
            "end": e,
            "all_day": all_day,
            "person_id": match_person(title, people),
            "recurring": 0,
            "updated": "",
            "color_id": color_id,
        })
    return rows
