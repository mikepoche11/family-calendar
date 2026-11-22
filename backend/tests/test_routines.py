from datetime import date

import pytest

from app.db import Database
from app.marbles import Marbles
from app.routines import Routines

MON, SAT = date(2026, 11, 16), date(2026, 11, 21)


@pytest.fixture()
def r(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    db.seed_people("Mike:#000000,Eppie Marie:#111111,Jordyn:#222222,Aaron:#333333")
    ids = {p["name"]: p["id"] for p in db.list_people()}
    m = Marbles(db)
    m.set_jars([ids["Eppie Marie"], ids["Jordyn"], ids["Aaron"]])
    return Routines(db, m), m, ids


def mine(day, kind, pid):
    return [s for s in day["steps"] if s["kind"] == kind and s["person_id"] == pid]


def test_starter_and_school_days(r):
    rt, _, ids = r
    kids = [ids["Eppie Marie"], ids["Jordyn"], ids["Aaron"]]
    assert rt.add_starter(kids) == 12 * 3
    mon = rt.for_day(MON)
    sat = rt.for_day(SAT)
    assert len(mine(mon, "morning", ids["Aaron"])) == 6
    assert len(mine(sat, "morning", ids["Aaron"])) == 5  # no backpack on Saturday
    assert len(mine(mon, "bedtime", ids["Aaron"])) == 6


def test_done_resets_each_day(r):
    rt, _, ids = r
    s = rt.create("morning", ids["Aaron"], "Brush teeth", "🪥")
    rt.set_done(s["id"], MON, True)
    assert mine(rt.for_day(MON), "morning", ids["Aaron"])[0]["done"]
    assert not mine(rt.for_day(date(2026, 11, 17)), "morning", ids["Aaron"])[0]["done"]


def test_step_marbles_and_finish_bonus(r):
    rt, m, ids = r
    a = ids["Aaron"]
    rt.set_settings({"morning": {"bonus": 3}})
    s1 = rt.create("morning", a, "Teeth", marbles=1)
    s2 = rt.create("morning", a, "Shoes")
    res = rt.set_done(s1["id"], MON, True)
    assert res == {"marbles": [{"person_id": a, "count": 1}], "finished": False, "bonus": 0}
    res = rt.set_done(s2["id"], MON, True)
    assert res == {"marbles": [{"person_id": a, "count": 3}], "finished": True, "bonus": 3}
    assert m.jar(a)["blue"] == 4
    assert rt.for_day(MON)["bonus"] == [{"kind": "morning", "person_id": a, "marbles": 3}]
    # Unchecking a step takes back its marbles and the bonus
    res = rt.set_done(s1["id"], MON, False)
    assert res["marbles"] == [{"person_id": a, "count": -4}] and not res["finished"]
    assert m.jar(a)["blue"] == 0 and m.history(a) == []
    # Finishing again gives the bonus again (once)
    rt.set_done(s1["id"], MON, True)
    assert m.jar(a)["blue"] == 4


def test_no_jar_no_marbles(r):
    rt, m, ids = r
    rt.set_settings({"bedtime": {"bonus": 2}})
    s = rt.create("bedtime", ids["Mike"], "Lock doors", marbles=2)
    res = rt.set_done(s["id"], MON, True)
    assert res["marbles"] == [] and res["finished"]


def test_settings_validation(r):
    rt, _, _ = r
    assert rt.settings()["morning"]["start"] == "06:00"
    with pytest.raises(ValueError):
        rt.set_settings({"morning": {"start": "10:00", "end": "09:00"}})
    with pytest.raises(ValueError):
        rt.set_settings({"bedtime": {"start": "07:00"}})  # overlaps the morning
    out = rt.set_settings({"bedtime": {"start": "19:30", "end": "20:45"}, "auto_show": False})
    assert out["bedtime"] == {"start": "19:30", "end": "20:45", "bonus": 0} and out["auto_show"] is False
    assert rt.settings() == out


def test_move_copy_delete(r):
    rt, _, ids = r
    a, j = ids["Aaron"], ids["Jordyn"]
    s1 = rt.create("bedtime", a, "Bath")
    s2 = rt.create("bedtime", a, "Teeth")
    rt.move(s2["id"], -1)
    assert [s["title"] for s in rt.list() if s["person_id"] == a] == ["Teeth", "Bath"]
    assert rt.copy(a, j, "bedtime") == 2
    assert [s["title"] for s in rt.list() if s["person_id"] == j] == ["Teeth", "Bath"]
    assert rt.delete(s1["id"]) and not rt.delete(s1["id"])
    with pytest.raises(ValueError):
        rt.create("noon", a, "x")


def test_api_round_trip(tmp_path, monkeypatch):
    import importlib

    from fastapi.testclient import TestClient

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "")
    monkeypatch.setenv("PEOPLE", "Mike:#3b82f6,Ava:#ec4899")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "nostatic"))
    import app.main

    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        ava = c.get("/api/people").json()[1]["id"]
        c.put("/api/marbles/jars", json={"person_ids": [ava]})
        assert c.post("/api/routines/starter", json={"kid_ids": [ava]}).json() == {"added": 12}
        step = c.post("/api/routines/steps", json={"kind": "morning", "person_id": ava, "title": "Feed fish", "marbles": 2}).json()
        r = c.post(f"/api/routines/steps/{step['id']}/done", json={"done": True}).json()
        assert r["marbles"][0]["count"] == 2 and r["marbles"][0]["jar"]["blue"] == 2
        today = c.get("/api/routines/today").json()
        assert any(s["done"] for s in today["steps"]) and today["settings"]["bedtime"]["end"] == "21:00"
        assert c.patch(f"/api/routines/steps/{step['id']}", json={"move": -1}).status_code == 200
        bad = c.put("/api/routines/settings", json={"morning": {"start": "09:00", "end": "08:00"}})
        assert bad.status_code == 422
        assert c.put("/api/routines/settings", json={"morning": {"bonus": 2}}).json()["morning"]["bonus"] == 2
        assert c.delete(f"/api/routines/steps/{step['id']}").status_code == 204
