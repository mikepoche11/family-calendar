"""Calendar stickers: decorations saved in the app, never sent to Google Calendar."""

from .test_api import client  # noqa: F401  (fixture)


def test_add_move_resize_delete(client):
    r = client.post("/api/stickers", json={"day": "2026-12-25", "icon": "xmas-tree", "x": 0.3, "y": 0.4})
    assert r.status_code == 201
    s = r.json()
    assert (s["day"], s["icon"], s["x"], s["y"], s["size"], s["rotation"]) == ("2026-12-25", "xmas-tree", 0.3, 0.4, 0.6, 0)

    # drag to another day, bigger and tilted; rotation is kept within -180..180
    r = client.patch(f"/api/stickers/{s['id']}", json={"day": "2026-12-24", "x": 1.2, "size": 1.5, "rotation": 370})
    assert r.json() | {"id": 0} == {"id": 0, "day": "2026-12-24", "icon": "xmas-tree", "x": 1.2, "y": 0.4, "size": 1.5, "rotation": 10}

    assert [x["id"] for x in client.get("/api/stickers?start=2026-12-21&end=2026-12-28").json()] == [s["id"]]
    assert client.get("/api/stickers?start=2026-12-25&end=2026-12-28").json() == []

    assert client.delete(f"/api/stickers/{s['id']}").status_code == 204
    assert client.get("/api/stickers").json() == []
    assert client.delete(f"/api/stickers/{s['id']}").status_code == 404


def test_rejects_bad_values(client):
    assert client.post("/api/stickers", json={"day": "Christmas", "icon": "xmas-tree"}).status_code == 422
    assert client.post("/api/stickers", json={"day": "2026-12-25", "icon": "<svg>"}).status_code == 422
    assert client.post("/api/stickers", json={"day": "2026-12-25", "icon": "star", "size": 50}).status_code == 422
    assert client.patch("/api/stickers/999", json={"x": 0.5}).status_code == 404


def test_stickers_never_touch_events(client):
    before = client.get("/api/events?start=2026-12-01T00:00:00Z&end=2027-01-01T00:00:00Z").json()
    client.post("/api/stickers", json={"day": "2026-12-25", "icon": "xmas-tree"})
    after = client.get("/api/events?start=2026-12-01T00:00:00Z&end=2027-01-01T00:00:00Z").json()
    assert after == before
