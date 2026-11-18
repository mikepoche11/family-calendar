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
