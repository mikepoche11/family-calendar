from datetime import date

import pytest

from app.db import Database
from app.shownight import ShowNight


@pytest.fixture()
def sn(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    db.seed_people("Mike:#000000,Eppie Marie:#111111,Jordyn:#222222,Aaron:#333333")
    ids = {p["name"]: p["id"] for p in db.list_people()}
    return ShowNight(db), ids, db


D = date.fromisoformat


def test_default_starts_on_aaron_and_alternates(sn):
    s, ids, _ = sn
    assert s.get(D("2026-11-22"))["tonight"] == ids["Aaron"]
    assert s.get(D("2026-11-22"))["tomorrow"] == ids["Jordyn"]
    assert s.get(D("2026-11-23"))["tonight"] == ids["Jordyn"]
    assert s.get(D("2026-11-24"))["tonight"] == ids["Aaron"]
    assert s.get(D("2026-12-25"))["tonight"] == ids["Jordyn"]  # 33 days later


def test_swap_shifts_turns(sn):
    s, ids, _ = sn
    out = s.swap(D("2026-11-25"))  # Jordyn's night, skipped
    assert out["tonight"] == ids["Aaron"]
    assert s.get(D("2026-11-26"))["tonight"] == ids["Jordyn"]
    assert s.swap(D("2026-11-25"))["tonight"] == ids["Jordyn"]  # tap again to undo


def test_set_order_keeps_tonight(sn):
    s, ids, _ = sn
    out = s.set_order([ids["Eppie Marie"], ids["Jordyn"], ids["Aaron"]], D("2026-11-22"))
    assert out["tonight"] == ids["Aaron"]
    assert s.get(D("2026-11-23"))["tonight"] == ids["Eppie Marie"]
    out = s.set_order([ids["Eppie Marie"], ids["Jordyn"]], D("2026-11-22"))
    assert out["tonight"] == ids["Eppie Marie"]


def test_removed_person_drops_out(sn):
    s, ids, db = sn
    s.set_order([ids["Aaron"], ids["Eppie Marie"], ids["Jordyn"]], D("2026-11-22"))
    db.delete_person(ids["Eppie Marie"])
    assert s.get(D("2026-11-22"))["tonight"] == ids["Aaron"]
    assert s.get(D("2026-11-23"))["tonight"] == ids["Jordyn"]


def test_empty(sn):
    s, _, _ = sn
    out = s.set_order([], D("2026-11-22"))
    assert out["tonight"] is None and out["order"] == []
    assert s.swap(D("2026-11-22"))["tonight"] is None
