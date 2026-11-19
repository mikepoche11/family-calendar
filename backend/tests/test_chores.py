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


@pytest.fixture()
def with_jars(tmp_path):
    from app.marbles import Marbles

    db = Database(tmp_path / "db.sqlite")
    db.seed_people("Mike:#000000,Eppie Marie:#111111,Jordyn:#222222,Aaron:#333333")
    ids = {p["name"]: p["id"] for p in db.list_people()}
    m = Marbles(db)
    m.set_jars([ids["Eppie Marie"], ids["Jordyn"], ids["Aaron"]])
    return Chores(db, m), m, ids


def test_marble_value_awards_and_takes_back(with_jars):
    c, m, ids = with_jars
    aaron = ids["Aaron"]
    bed = c.create("Make bed", "", aaron, "0123456", marbles=2)
    assert bed["marbles"] == 2
    assert c.set_done(bed["id"], MON, True, None) == {"marbles": [{"person_id": aaron, "count": 2}]}
    assert m.jar(aaron)["blue"] == 2
    assert {x["id"]: x for x in c.for_day(MON)}[bed["id"]]["marbles_given"] == 2
    # Misclick: unchecking takes them back and leaves no trace in the jar's history
    assert c.set_done(bed["id"], MON, False, None) == {"marbles": [{"person_id": aaron, "count": -2}]}
    assert m.jar(aaron)["blue"] == 0 and m.history(aaron) == []


def test_take_back_after_other_changes(with_jars):
    c, m, ids = with_jars
    j = ids["Jordyn"]
    trash = c.create("Trash", "", None, "0123456", marbles=3)
    c.set_done(trash["id"], MON, True, j)
    m.add(j, "white")
    c.set_done(trash["id"], MON, False, None)
    jar = m.jar(j)
    assert (jar["blue"], jar["white"]) == (0, 1)  # whites are not touched
    assert m.history(j)[0]["action"] == "unchore"


def test_take_back_never_goes_below_zero_or_twice(with_jars):
    c, m, ids = with_jars
    e = ids["Eppie Marie"]
    dishes = c.create("Dishes", "", e, "0123456", marbles=5)
    c.set_done(dishes["id"], MON, True, None)
    m.spend(e, m.rewards()[0]["id"])  # big ice cream, 5 blue
    c.set_done(dishes["id"], MON, False, None)
    assert m.jar(e)["contents"] == ""
    # Undo last after a chore award, then uncheck: nothing extra is taken
    c.set_done(dishes["id"], date(2026, 11, 17), True, None)
    m.add(e, "blue")
    m.undo(e)
    m.undo(e)  # removes the chore award
    m.add(e, "blue")
    c.set_done(dishes["id"], date(2026, 11, 17), False, None)
    assert m.jar(e)["blue"] == 1


def test_no_jar_or_zero_value_gives_nothing(with_jars):
    c, m, ids = with_jars
    mow = c.create("Mow", "", ids["Mike"], "0123456", marbles=4)  # parents have no jar
    bed = c.create("Bed", "", ids["Aaron"], "0123456")
    assert c.set_done(mow["id"], MON, True, None) == {"marbles": []}
    assert c.set_done(bed["id"], MON, True, None) == {"marbles": []}
    assert m.jar(ids["Aaron"])["blue"] == 0
    with pytest.raises(ValueError):
        c.update(bed["id"], {"marbles": 21})
    assert c.update(bed["id"], {"marbles": 1})["marbles"] == 1


def test_anyone_chore_reassigned(with_jars):
    c, m, ids = with_jars
    trash = c.create("Trash", "", None, "0123456", marbles=1)
    c.set_done(trash["id"], MON, True, ids["Jordyn"])
    c.set_done(trash["id"], MON, True, ids["Aaron"])
    assert m.jar(ids["Jordyn"])["blue"] == 0 and m.jar(ids["Aaron"])["blue"] == 1
