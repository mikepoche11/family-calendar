"""Countdowns: name, date, icon; once or every year, including holidays that move around."""

from datetime import date

from app.countdowns import easter, next_date, on_year

from .test_api import client  # noqa: F401  (fixture)


def test_moving_holidays():
    assert easter(2027) == date(2027, 3, 28)
    assert easter(2026) == date(2026, 4, 5)
    assert on_year("mardi-gras", date(2000, 1, 1), 2027) == date(2027, 2, 9)
    assert on_year("mardi-gras", date(2000, 1, 1), 2026) == date(2026, 2, 17)
    assert on_year("thanksgiving", date(2000, 1, 1), 2026) == date(2026, 11, 26)
    assert on_year("thanksgiving", date(2000, 1, 1), 2027) == date(2027, 11, 25)


def test_next_date():
    today = date(2026, 11, 22)
    assert next_date("yearly", date(2020, 12, 25), today) == date(2026, 12, 25)
    assert next_date("yearly", date(2020, 3, 4), today) == date(2027, 3, 4)
    assert next_date("yearly", date(2020, 11, 22), today) == today  # today counts
    assert next_date("yearly", date(2024, 2, 29), today) == date(2027, 2, 28)
    assert next_date("", date(2026, 5, 1), today) == date(2026, 5, 1)  # a past one-off stays put
    assert next_date("thanksgiving", date(2000, 1, 1), date(2026, 11, 27)) == date(2027, 11, 25)


def test_add_edit_remove(client):
    r = client.post("/api/countdowns", json={"name": " Disney trip ", "day": "2099-06-01", "icon": "summer-sun"})
    assert r.status_code == 201
    c = r.json()
    assert (c["name"], c["day"], c["icon"], c["repeat"], c["next"]) == ("Disney trip", "2099-06-01", "summer-sun", "", "2099-06-01")
    assert c["days"] > 0

    r = client.patch(f"/api/countdowns/{c['id']}", json={"name": "Beach trip", "repeat": "yearly"})
    assert (r.json()["name"], r.json()["repeat"]) == ("Beach trip", "yearly")

    data = client.get("/api/countdowns").json()
    assert [x["id"] for x in data["countdowns"]] == [c["id"]]

    assert client.delete(f"/api/countdowns/{c['id']}").status_code == 204
    assert client.get("/api/countdowns").json()["countdowns"] == []
    assert client.delete(f"/api/countdowns/{c['id']}").status_code == 404
    assert client.patch(f"/api/countdowns/{c['id']}", json={"name": "x"}).status_code == 404


def test_sorted_soonest_first_and_past_last(client):
    client.post("/api/countdowns", json={"name": "Far", "day": "2099-01-01"})
    client.post("/api/countdowns", json={"name": "Old", "day": "2001-01-01"})
    client.post("/api/countdowns", json={"name": "Near", "day": "2098-01-01"})
    names = [x["name"] for x in client.get("/api/countdowns").json()["countdowns"]]
    assert names == ["Near", "Far", "Old"]


def test_holidays_added_once(client):
    r = client.post("/api/countdowns/holidays").json()
    assert r["added"] == 7
    rows = client.get("/api/countdowns").json()["countdowns"]
    xmas = next(x for x in rows if x["name"] == "Christmas")
    assert xmas["repeat"] == "yearly" and xmas["next"].endswith("-12-25") and 0 <= xmas["days"] <= 366
    assert all(0 <= x["days"] <= 366 for x in rows)
    assert client.post("/api/countdowns/holidays").json()["added"] == 0


def test_rejects_bad_values(client):
    assert client.post("/api/countdowns", json={"name": "", "day": "2099-01-01"}).status_code == 422
    assert client.post("/api/countdowns", json={"name": "X", "day": "soon"}).status_code == 422
    assert client.post("/api/countdowns", json={"name": "X", "day": "2099-02-30"}).status_code == 422
    assert client.post("/api/countdowns", json={"name": "X", "day": "2099-01-01", "repeat": "weekly"}).status_code == 422
