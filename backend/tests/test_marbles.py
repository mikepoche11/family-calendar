import pytest

from app.db import Database
from app.marbles import MarbleError, Marbles, remove_top


@pytest.fixture()
def jars(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    db.seed_people("Mike:#000000,Eppie Marie:#111111,Jordyn:#222222,Aaron:#333333")
    ids = {p["name"]: p["id"] for p in db.list_people()}
    m = Marbles(db)
    m.set_jars([ids["Eppie Marie"], ids["Jordyn"], ids["Aaron"]])
    return m, ids, db


def test_remove_top_takes_newest_of_color():
    assert remove_top("bwbwb", "b", 2) == "bww"
    assert remove_top("bwbwb", "w", 1) == "bwbb"


def test_default_rewards(jars):
    m, _, _ = jars
    assert [(r["title"], r["cost"]) for r in m.rewards()] == [
        ("Big ice cream", 5), ("Small ice cream", 3), ("Coke", 3), ("Sprite", 3), ("Dr Pepper", 3),
    ]


def test_whites_stay_until_cancel_out(jars):
    m, ids, _ = jars
    ava = ids["Eppie Marie"]
    m.add(ava, "blue", 5)
    jar = m.add(ava, "white", 3)
    assert (jar["blue"], jar["white"]) == (5, 3)  # adding white doesn't remove blue
    jar = m.cancel(ava)
    assert (jar["blue"], jar["white"], jar["contents"]) == (2, 0, "bb")
    with pytest.raises(MarbleError):
        m.cancel(ava)


def test_extra_whites_remain(jars):
    m, ids, _ = jars
    j = ids["Jordyn"]
    m.add(j, "blue", 2)
    m.add(j, "white", 5)
    jar = m.cancel(j)
    assert (jar["blue"], jar["white"]) == (0, 3)


def test_spend(jars):
    m, ids, _ = jars
    a = ids["Aaron"]
    big = next(r for r in m.rewards() if r["title"] == "Big ice cream")
    m.add(a, "blue", 4)
    with pytest.raises(MarbleError):
        m.spend(a, big["id"])
    m.add(a, "white", 1)
    m.add(a, "blue", 2)
    jar = m.spend(a, big["id"])
    assert (jar["blue"], jar["white"], jar["contents"]) == (1, 1, "bw")
    assert m.history(a)[0]["note"] == "Big ice cream"


def test_undo_restores_previous(jars):
    m, ids, _ = jars
    a = ids["Aaron"]
    m.add(a, "blue", 3)
    m.add(a, "white", 3)
    m.cancel(a)
    assert m.undo(a)["contents"] == "bbbwww"
    assert m.undo(a)["contents"] == "bbb"
    m.undo(a)
    with pytest.raises(MarbleError):
        m.undo(a)


def test_jars_keep_marbles_and_order(jars):
    m, ids, _ = jars
    m.add(ids["Aaron"], "blue", 2)
    m.set_jars([ids["Aaron"], ids["Jordyn"], ids["Eppie Marie"]])
    got = m.jars()
    assert [j["person_id"] for j in got] == [ids["Aaron"], ids["Jordyn"], ids["Eppie Marie"]]
    assert got[0]["blue"] == 2


def test_deleting_person_removes_jar(jars):
    m, ids, db = jars
    m.add(ids["Aaron"], "blue", 1)
    db.delete_person(ids["Aaron"])
    assert ids["Aaron"] not in [j["person_id"] for j in m.jars()]
