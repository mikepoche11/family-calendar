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
    assert client.patch(f"/api/chores/{bed['id']}", json={"anyone": True}).json()["person_id"] is None
    assert client.post("/api/chores", json={"title": "x", "days": "78"}).status_code == 422
    assert client.post("/api/chores", json={"title": "x", "person_id": 999}).status_code == 422
