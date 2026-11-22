"""API tests in demo mode (no Google credentials)."""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "")
    monkeypatch.setenv("PEOPLE", "Mike:#3b82f6,Ava:#ec4899,Family:#64748b")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "nostatic"))
    import app.main

    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        app.main.app.state.s.sync_now.set()
        yield c


def test_health_demo(client):
    assert client.get("/api/health").json()["mode"] == "demo"


def test_people_seeded(client):
    names = [p["name"] for p in client.get("/api/people").json()]
    assert names == ["Mike", "Ava", "Family"]


def test_bright_colors_switch_to_pastel_once(client):
    colors = [p["color"] for p in client.get("/api/people").json()]
    assert colors == ["#93c5fd", "#f9a8d4", "#cbd5e1"]
    import app.main

    db = app.main.app.state.s.db
    mike = client.get("/api/people").json()[0]
    client.patch(f"/api/people/{mike['id']}", json={"color": "#2563eb"})
    db.pastelize_people()  # already done: a colour picked later is left alone
    assert client.get("/api/people").json()[0]["color"] == "#2563eb"


def test_pastel_mixes_unknown_colors():
    from app.db import pastel

    assert pastel("#fde68a") == "#fde68a"
    assert pastel("#000000") == "#8c8c8c"


def test_demo_events_have_owners(client):
    import asyncio

    import app.main

    asyncio.run(app.main.app.state.s.sync_once())
    events = client.get("/api/events", params={"start": "0000", "end": "9999"}).json()
    assert len(events) > 5
    assert any(e["person_id"] is not None for e in events)


def test_create_update_delete_event(client):
    people = client.get("/api/people").json()
    ava = next(p for p in people if p["name"] == "Ava")
    r = client.post(
        "/api/events",
        json={"summary": "Piano", "start": "2026-12-01T16:00", "end": "2026-12-01T17:00", "person_id": ava["id"]},
    )
    assert r.status_code == 201, r.text
    ev = r.json()
    assert ev["summary"] == "Ava: Piano"
    assert ev["person_id"] == ava["id"]
    assert ev["start"] == "2026-12-01T22:00:00Z"  # 4 PM Central

    r = client.patch(
        f"/api/events/{ev['id']}",
        json={"summary": "Ava: Piano recital", "start": "2026-12-01", "end": "2026-12-02", "all_day": True},
    )
    assert r.status_code == 200 and r.json()["all_day"] is True

    assert client.delete(f"/api/events/{ev['id']}").status_code == 204
    assert client.delete(f"/api/events/{ev['id']}").status_code == 404


def test_event_color(client):
    r = client.post(
        "/api/events",
        json={"summary": "Gym", "start": "2026-12-01T16:00", "end": "2026-12-01T17:00", "color_id": "11"},
    )
    assert r.status_code == 201 and r.json()["color_id"] == "11"
    ev = r.json()
    r = client.patch(
        f"/api/events/{ev['id']}",
        json={"summary": "Gym", "start": "2026-12-01T16:00", "end": "2026-12-01T17:00", "color_id": ""},
    )
    assert r.json()["color_id"] == ""
    bad = {"summary": "x", "start": "2026-12-01T16:00", "end": "2026-12-01T17:00", "color_id": "12"}
    assert client.post("/api/events", json=bad).status_code == 422


def test_demo_events_have_google_colors(client):
    rows = client.get("/api/events", params={"start": "2000-01-01T00:00:00Z", "end": "2100-01-01T00:00:00Z"}).json()
    assert rows and all(r["color_id"] for r in rows)


def test_event_must_end_after_start(client):
    r = client.post("/api/events", json={"summary": "x", "start": "2026-12-01T17:00", "end": "2026-12-01T16:00"})
    assert r.status_code == 422


def test_renaming_person_reassigns_events(client):
    client.post("/api/events", json={"summary": "Mom: Yoga", "start": "2026-12-02T09:00", "end": "2026-12-02T10:00"})
    mom = client.post("/api/people", json={"name": "Mom", "color": "#22c55e"}).json()
    events = client.get("/api/events", params={"start": "2026-12-02", "end": "2026-12-03"}).json()
    yoga = next(e for e in events if e["summary"] == "Mom: Yoga")
    assert yoga["person_id"] == mom["id"]


def test_person_avatar_and_color(client):
    mike = client.get("/api/people").json()[0]
    assert mike["avatar"] == ""
    r = client.patch(f"/api/people/{mike['id']}", json={"avatar": "fox", "color": "#ea7a2b"})
    assert r.status_code == 200
    assert r.json()["avatar"] == "fox" and r.json()["color"] == "#ea7a2b" and r.json()["name"] == "Mike"
    assert client.patch(f"/api/people/{mike['id']}", json={"avatar": "<script>"}).status_code == 422
    assert client.patch(f"/api/people/{mike['id']}", json={"color": "red"}).status_code == 422


def test_old_database_gets_avatar_column(tmp_path):
    import sqlite3

    from app.db import Database

    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT UNIQUE, color TEXT, position INTEGER)")
    conn.execute("INSERT INTO people(name, color, position) VALUES('Mike', '#000000', 0)")
    conn.commit()
    conn.close()
    assert Database(path).list_people()[0]["avatar"] == ""


def test_old_database_gets_event_color_column(tmp_path):
    import sqlite3

    from app.db import Database

    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE events (id TEXT PRIMARY KEY, summary TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', "
        "location TEXT NOT NULL DEFAULT '', start TEXT NOT NULL, end TEXT NOT NULL, all_day INTEGER NOT NULL DEFAULT 0, "
        "person_id INTEGER, recurring INTEGER NOT NULL DEFAULT 0, updated TEXT NOT NULL DEFAULT '')"
    )
    conn.execute("INSERT INTO events(id, summary, start, end) VALUES('e1', 'Gym', '2026-12-01', '2026-12-02')")
    conn.commit()
    conn.close()
    assert Database(path).get_event("e1")["color_id"] == ""


def test_grocery_list(client):
    milk = client.post("/api/grocery", json={"text": " Milk "}).json()
    assert milk["text"] == "Milk" and milk["done"] is False
    assert client.post("/api/grocery", json={"text": "milk"}).json()["id"] == milk["id"]  # no duplicates
    eggs = client.post("/api/grocery", json={"text": "Eggs"}).json()
    assert [i["text"] for i in client.get("/api/grocery").json()] == ["Eggs", "Milk"]

    r = client.patch(f"/api/grocery/{milk['id']}", json={"done": True})
    assert r.json()["done"] is True and r.json()["done_at"]
    assert [i["text"] for i in client.get("/api/grocery").json()] == ["Eggs", "Milk"]  # checked go last
    client.patch(f"/api/grocery/{eggs['id']}", json={"done": True})
    client.patch(f"/api/grocery/{eggs['id']}", json={"done": False})
    assert client.get("/api/grocery").json()[0]["done"] is False

    assert client.post("/api/grocery/clear-checked").json() == {"deleted": 1}
    assert [i["text"] for i in client.get("/api/grocery").json()] == ["Eggs"]
    assert client.post("/api/grocery", json={"text": "   "}).status_code == 422
    assert client.delete(f"/api/grocery/{eggs['id']}").status_code == 204
    assert client.get("/api/grocery").json() == []


def test_chores_api(client):
    people = {p["name"]: p["id"] for p in client.get("/api/people").json()}
    r = client.post("/api/chores/starter", json={"kid_ids": [people["Ava"]]})
    assert r.status_code == 201 and r.json()["added"] == 8
    today = client.get("/api/chores/today").json()
    bed = next(c for c in today["chores"] if c["title"] == "Make bed")
    assert client.post(f"/api/chores/{bed['id']}/done", json={"done": True}).status_code == 200
    again = client.get("/api/chores/today").json()
    assert next(c for c in again["chores"] if c["id"] == bed["id"])["done_by"] == people["Ava"]
    assert client.patch(f"/api/chores/{bed['id']}", json={"marbles": 21}).status_code == 422
    assert client.patch(f"/api/chores/{bed['id']}", json={"anyone": True}).json()["person_id"] is None
    assert client.post("/api/chores", json={"title": "x", "days": "78"}).status_code == 422
    assert client.post("/api/chores", json={"title": "x", "person_id": 999}).status_code == 422


def test_marbles_api(client):
    people = {p["name"]: p["id"] for p in client.get("/api/people").json()}
    ava = people["Ava"]
    assert client.put("/api/marbles/jars", json={"person_ids": [ava]}).status_code == 200
    data = client.get("/api/marbles").json()
    assert data["jars"][0]["person_id"] == ava and len(data["rewards"]) == 5
    assert client.post(f"/api/marbles/{ava}/add", json={"color": "blue", "count": 3}).json()["blue"] == 3
    assert client.post(f"/api/marbles/{ava}/add", json={"color": "red"}).status_code == 422
    coke = next(r for r in data["rewards"] if r["title"] == "Coke")
    big = next(r for r in data["rewards"] if r["title"] == "Big ice cream")
    assert client.post(f"/api/marbles/{ava}/spend", json={"reward_id": big["id"]}).status_code == 409
    assert client.post(f"/api/marbles/{ava}/spend", json={"reward_id": coke["id"]}).json()["blue"] == 0
    client.post(f"/api/marbles/{ava}/add", json={"color": "white"})
    assert client.post(f"/api/marbles/{ava}/cancel").status_code == 409
    assert client.post(f"/api/marbles/{ava}/undo").json()["white"] == 0
    assert client.post("/api/marbles/999/add", json={"color": "blue"}).status_code == 404
    assert client.put("/api/marbles/jars", json={"person_ids": [999]}).status_code == 422
    r = client.post("/api/rewards", json={"title": "Movie night", "icon": "🎬", "cost": 10}).json()
    assert client.patch(f"/api/rewards/{r['id']}", json={"cost": 8}).json()["cost"] == 8
    assert client.delete(f"/api/rewards/{r['id']}").status_code == 204


def test_chore_marbles_api(client):
    ava = {p["name"]: p["id"] for p in client.get("/api/people").json()}["Ava"]
    client.put("/api/marbles/jars", json={"person_ids": [ava]})
    chore = client.post("/api/chores", json={"title": "Feed dog", "person_id": ava, "marbles": 2}).json()
    assert chore["marbles"] == 2
    r = client.post(f"/api/chores/{chore['id']}/done", json={"done": True}).json()
    assert r["marbles"][0]["count"] == 2 and r["marbles"][0]["jar"]["blue"] == 2
    r = client.post(f"/api/chores/{chore['id']}/done", json={"done": False}).json()
    assert r["marbles"][0]["count"] == -2 and r["marbles"][0]["jar"]["blue"] == 0


def test_theme_saved_and_shared(client):
    assert client.get("/api/config").json()["theme"] == ""
    assert client.put("/api/theme", json={"theme": "halloween"}).json() == {"theme": "halloween"}
    assert client.get("/api/config").json()["theme"] == "halloween"
    assert client.put("/api/theme", json={"theme": "Bad Theme!"}).status_code == 422
    assert client.put("/api/theme", json={"theme": ""}).status_code == 200
    assert client.get("/api/config").json()["theme"] == ""


def test_holiday_icon_and_avatar_ids_fit(client):
    mike = client.get("/api/people").json()[0]
    r = client.patch(f"/api/people/{mike['id']}", json={"avatar": "halloween-candy-corn"})
    assert r.status_code == 200 and r.json()["avatar"] == "halloween-candy-corn"
    r = client.post("/api/chores", json={"title": "Carve pumpkin", "icon": "halloween-pumpkin"})
    assert r.status_code in (200, 201) and r.json()["icon"] == "halloween-pumpkin"


def test_theme_background_custom_and_reset(client):
    assert client.get("/api/config").json()["theme_backgrounds"] == {}
    r = client.put("/api/theme/background", json={"theme": "christmas", "color": "#2F6B45"})
    assert r.json()["theme_backgrounds"] == {"christmas": "#2f6b45"}
    client.put("/api/theme/background", json={"theme": "", "color": "#ffeedd"})
    assert client.get("/api/config").json()["theme_backgrounds"] == {"christmas": "#2f6b45", "": "#ffeedd"}
    assert client.put("/api/theme/background", json={"theme": "christmas", "color": "green"}).status_code == 422
    client.put("/api/theme/background", json={"theme": "christmas", "color": ""})
    assert client.get("/api/config").json()["theme_backgrounds"] == {"": "#ffeedd"}


def test_show_night_api(client):
    people = {p["name"]: p["id"] for p in client.get("/api/people").json()}
    # No Aaron/Jordyn in this family: nobody until a list is set
    assert client.get("/api/marbles").json()["show_night"]["tonight"] is None
    out = client.put("/api/show-night", json={"person_ids": [people["Ava"], people["Mike"]]}).json()
    assert out["tonight"] == people["Ava"] and out["tomorrow"] == people["Mike"]
    assert client.post("/api/show-night/swap").json()["tonight"] == people["Mike"]
    assert client.get("/api/show-night").json()["tonight"] == people["Mike"]
    assert client.put("/api/show-night", json={"person_ids": [999]}).status_code == 422
