from datetime import date

import pytest

from app.chores import Chores
from app.db import Database


@pytest.fixture()
def chores(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    db.seed_people("Mike:#000000,Eppie Marie:#111111,Jordyn:#222222,Aaron:#333333")
    return Chores(db), {p["name"]: p["id"] for p in db.list_people()}


MON, SAT = date(2026, 11, 16), date(2026, 11, 21)


def test_starter_set(chores):
    c, ids = chores
    kids = [ids["Eppie Marie"], ids["Jordyn"], ids["Aaron"]]
    assert c.add_starter(kids) == 5 * 3 + 3
    monday = c.for_day(MON)
    saturday = c.for_day(SAT)
    assert not any(x["title"] == "Tidy bedroom" for x in monday)
    assert sum(x["title"] == "Tidy bedroom" for x in saturday) == 3
    assert sum(x["person_id"] is None for x in monday) == 3  # anyone chores


def test_done_per_day(chores):
    c, ids = chores
    bed = c.create("Make bed", "", ids["Aaron"], "0123456")
    trash = c.create("Trash", "", None, "0123456")
    assert c.set_done(bed["id"], MON, True, None)
    assert c.set_done(trash["id"], MON, True, ids["Jordyn"])
    mon = {x["id"]: x for x in c.for_day(MON)}
    assert mon[bed["id"]]["done"] and mon[bed["id"]]["done_by"] == ids["Aaron"]
    assert mon[trash["id"]]["done_by"] == ids["Jordyn"]
    tue = {x["id"]: x for x in c.for_day(date(2026, 11, 17))}
    assert not tue[bed["id"]]["done"]  # a new day starts unchecked
    c.set_done(bed["id"], MON, False, None)
    assert not {x["id"]: x for x in c.for_day(MON)}[bed["id"]]["done"]


def test_days_validation_and_update(chores):
    c, ids = chores
    with pytest.raises(ValueError):
        c.create("x", "", None, "9")
    ch = c.create("Dishes", "", None, "6620")
    assert ch["days"] == "026"
    assert c.update(ch["id"], {"person_id": ids["Mike"], "days": "5"})["days"] == "5"
    assert c.delete(ch["id"]) and not c.delete(ch["id"])
