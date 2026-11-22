from app.events import from_google, match_person, titled_for, to_google, to_utc_iso

PEOPLE = [
    {"id": 1, "name": "Mike", "color": "#3b82f6"},
    {"id": 2, "name": "Ava", "color": "#ec4899"},
    {"id": 3, "name": "Family", "color": "#64748b"},
]


def test_match_colon_prefix():
    assert match_person("Mike: Dentist", PEOPLE) == 1


def test_match_brackets():
    assert match_person("Soccer [Ava]", PEOPLE) == 2


def test_match_first_name_wins():
    assert match_person("Ava & Mike: Recital", PEOPLE) == 2


def test_case_insensitive():
    assert match_person("ava - piano", PEOPLE) == 2


def test_no_match_inside_words():
    assert match_person("Mikeys birthday", PEOPLE) is None
    assert match_person("Pick up groceries", PEOPLE) is None


def test_to_utc_iso():
    assert to_utc_iso("2026-11-18T16:00:00-06:00") == "2026-11-18T22:00:00Z"


def test_from_google_timed():
    row = from_google(
        {
            "id": "abc",
            "summary": "Mike: Gym",
            "start": {"dateTime": "2026-11-18T18:30:00-06:00"},
            "end": {"dateTime": "2026-11-18T19:30:00-06:00"},
            "recurringEventId": "base",
        },
        PEOPLE,
    )
    assert row["start"] == "2026-11-19T00:30:00Z"
    assert row["person_id"] == 1
    assert row["all_day"] == 0
    assert row["recurring"] == 1


def test_from_google_all_day_and_cancelled():
    row = from_google({"id": "x", "start": {"date": "2026-11-20"}, "end": {"date": "2026-11-21"}}, PEOPLE)
    assert row["all_day"] == 1 and row["summary"] == "(no title)"
    assert from_google({"id": "y", "status": "cancelled"}, PEOPLE) is None


def test_to_google():
    body = to_google({"summary": "x", "start": "2026-11-18T09:00", "end": "2026-11-18T10:00"}, "America/Chicago")
    assert body["start"] == {"dateTime": "2026-11-18T09:00", "timeZone": "America/Chicago"}
    body = to_google({"summary": "x", "all_day": True, "start": "2026-11-18", "end": "2026-11-19"}, "UTC")
    assert body["start"] == {"date": "2026-11-18"}


def test_titled_for():
    assert titled_for("Dentist", PEOPLE[0], PEOPLE) == "Mike: Dentist"
    assert titled_for("Mike: Dentist", PEOPLE[0], PEOPLE) == "Mike: Dentist"
    assert titled_for("Dentist", None, PEOPLE) == "Dentist"


def test_weather_shape():
    from app.weather import Weather

    raw = {
        "current": {"temperature_2m": 63.6, "weather_code": 2},
        "daily": {
            "time": ["2026-11-18", "2026-11-19"],
            "weather_code": [2, 61],
            "temperature_2m_max": [68.2, 70.0],
            "temperature_2m_min": [50.4, 52.0],
            "precipitation_probability_max": [5, 80],
        },
    }
    w = Weather.shape(raw)
    assert w["temperature"] == 64 and w["icon"] == "cloud-sun"
    assert w["days"][1] == {"date": "2026-11-19", "high": 70, "low": 52, "precip": 80, "label": "Rain", "icon": "rain"}


def test_from_google_keeps_event_color():
    item = {"id": "c", "summary": "Gym", "start": {"date": "2026-11-18"}, "end": {"date": "2026-11-19"}}
    assert from_google(item, PEOPLE)["color_id"] == ""
    assert from_google(item | {"colorId": "5"}, PEOPLE)["color_id"] == "5"


def test_to_google_sends_color():
    base = {"summary": "Gym", "start": "2026-11-18", "end": "2026-11-19", "all_day": True}
    assert "colorId" not in to_google(base, "America/Chicago")
    assert to_google(base | {"color_id": "11"}, "America/Chicago")["colorId"] == "11"
    assert to_google(base | {"color_id": ""}, "America/Chicago")["colorId"] is None  # clears on patch
