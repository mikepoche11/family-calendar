import asyncio
import importlib
import random
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.mealdb import IdeasError, MealIdeas, shape
from app.meals import Meals, week_start

MON = date(2026, 11, 16)


@pytest.fixture()
def meals(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    return Meals(db), db


def test_meal_box_and_plan(meals):
    m, _ = meals
    tacos = m.create("Tacos", "🌮", ["Ground beef", " ground beef ", "", "Shells"])
    assert tacos["ingredients"] == ["Ground beef", "Shells"]
    assert m.create("tacos")["id"] == tacos["id"]  # same name: no duplicate
    assert m.set_day(MON, tacos["id"])
    assert not m.set_day(MON, 9999)
    week = m.week(MON)
    assert [d["date"] for d in week][0] == "2026-11-16" and len(week) == 7
    assert week[0]["meal"]["name"] == "Tacos" and week[1]["meal"] is None
    m.set_day(MON, None)
    assert m.week(MON)[0]["meal"] is None


def test_deleting_a_meal_clears_its_nights(meals):
    m, _ = meals
    pizza = m.create("Pizza", "🍕", ["Dough"])
    m.set_day(MON, pizza["id"])
    assert m.delete(pizza["id"])
    assert m.week(MON)[0]["meal"] is None


def test_starter_and_fill_week(meals):
    m, _ = meals
    assert m.add_starter() == 11
    assert m.add_starter() == 0  # running it again adds nothing
    leftovers = next(x for x in m.list() if x["name"] == "Leftovers")
    m.set_day(date(2026, 11, 20), leftovers["id"])
    assert m.fill_week(MON, random.Random(1)) == 6
    week = m.week(MON)
    names = [d["meal"]["name"] for d in week]
    assert len(set(names)) == 7  # no repeats
    assert names[4] == "Leftovers"
    assert "Eating out" not in names


def test_week_start():
    assert week_start(date(2026, 11, 22)) == MON  # Sunday belongs to the week that started Monday
    assert week_start(MON) == MON


def test_grocery_lines_skip_items_already_listed(meals):
    _, db = meals
    db.add_grocery("Onion")
    db.add_grocery("Milk")
    db.update_grocery(db.list_grocery()[0]["id"], done=True)  # Milk checked off (bought)
    result = db.add_grocery_lines(["Onion (2)", "Milk", "Rice", "rice (1 cup)"])
    assert result == {"added": ["Milk", "Rice"], "skipped": ["Onion (2)", "rice (1 cup)"]}


SAMPLE = {
    "idMeal": "52772",
    "strMeal": "Teriyaki Chicken Casserole",
    "strCategory": "Chicken",
    "strArea": "Japanese",
    "strMealThumb": "https://www.themealdb.com/images/media/meals/x.jpg",
    "strSource": "",
    "strIngredient1": "soy sauce",
    "strMeasure1": "3/4 cup",
    "strIngredient2": "Rice",
    "strMeasure2": " ",
    "strIngredient3": "",
    "strMeasure3": "",
    "strIngredient4": None,
}


def test_shape():
    idea = shape(SAMPLE)
    assert idea["name"] == "Teriyaki Chicken Casserole"
    assert idea["ingredients"] == ["Soy sauce (3/4 cup)", "Rice"]
    assert idea["url"] == "https://www.themealdb.com/meal/52772"


def mock_transport(fail=False):
    counter = {"n": 0}

    def handler(request: httpx.Request):
        if fail:
            return httpx.Response(500)
        path = request.url.path
        if path.endswith("random.php"):
            counter["n"] += 1
            cat = "Dessert" if counter["n"] == 1 else "Chicken"
            return httpx.Response(200, json={"meals": [SAMPLE | {"idMeal": str(counter["n"]), "strCategory": cat}]})
        if path.endswith("search.php"):
            return httpx.Response(200, json={"meals": [SAMPLE]})
        if path.endswith("filter.php"):
            return httpx.Response(200, json={"meals": [{"idMeal": "52772"}, {"idMeal": "7"}]})
        if path.endswith("lookup.php"):
            return httpx.Response(200, json={"meals": [SAMPLE | {"idMeal": request.url.params["i"]}]})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_ideas_random_skips_desserts():
    ideas = asyncio.run(MealIdeas(mock_transport()).random(3))
    assert len(ideas) == 3
    assert all(i["category"] != "Dessert" for i in ideas)
    assert len({i["ext_id"] for i in ideas}) == 3


def test_ideas_search_adds_ingredient_matches():
    ideas = asyncio.run(MealIdeas(mock_transport()).search("chicken"))
    assert [i["ext_id"] for i in ideas] == ["52772", "7"]


def test_ideas_offline():
    with pytest.raises(IdeasError):
        asyncio.run(MealIdeas(mock_transport(fail=True)).random())


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "nostatic"))
    import app.main

    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        app.main.app.state.s.ideas = MealIdeas(mock_transport())
        yield c


def test_api_plan_and_grocery(client):
    meal = client.post("/api/meals", json={"name": "Gumbo", "ingredients": ["Roux", "Okra"]}).json()
    assert client.put("/api/meal-plan/2026-11-18", json={"meal_id": meal["id"]}).status_code == 200
    plan = client.get("/api/meal-plan", params={"start": "2026-11-19"}).json()
    assert plan["start"] == "2026-11-16"
    assert plan["days"][2]["meal"]["name"] == "Gumbo"
    assert client.put("/api/meal-plan/2026-11-18", json={"meal_id": 999}).status_code == 404
    assert client.put("/api/meal-plan/nope", json={"meal_id": None}).status_code == 422
    r = client.post("/api/grocery/bulk", json={"items": meal["ingredients"]}).json()
    assert r["added"] == ["Roux", "Okra"]
    assert len(client.get("/api/grocery").json()) == 2
    edited = client.patch(f"/api/meals/{meal['id']}", json={"ingredients": ["Roux", "Okra", "Shrimp"]}).json()
    assert edited["ingredients"][-1] == "Shrimp"
    assert client.post("/api/meals", json={"name": "Bad", "url": "javascript:alert(1)"}).status_code == 422
    assert client.delete(f"/api/meals/{meal['id']}").status_code == 204


def test_api_ideas_and_fill(client):
    assert len(client.get("/api/meals/ideas").json()["ideas"]) == 4
    assert client.get("/api/meals/ideas", params={"q": "chicken"}).json()["ideas"][0]["name"]
    assert client.post("/api/meals/starter").json()["added"] == 11
    assert client.post("/api/meal-plan/fill", params={"start": "2026-11-16"}).json()["filled"] == 7
