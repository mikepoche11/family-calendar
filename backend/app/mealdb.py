"""Dinner ideas from TheMealDB (https://www.themealdb.com): free, no sign-up, a few hundred meals with photos.

Uses the public test key "1", which TheMealDB allows for personal and learning projects.
"""

from __future__ import annotations

import asyncio

import httpx

BASE = "https://www.themealdb.com/api/json/v1/1"
# Categories that rarely suit a family weeknight; skipped when picking random ideas
SKIP_CATEGORIES = {"Dessert", "Goat", "Starter", "Side", "Breakfast"}


class IdeasError(Exception):
    pass


def shape(m: dict) -> dict:
    """TheMealDB meal -> {name, category, area, image, url, ingredients}."""
    ingredients = []
    for i in range(1, 21):
        name = (m.get(f"strIngredient{i}") or "").strip()
        measure = (m.get(f"strMeasure{i}") or "").strip()
        if name:
            line = f"{name[:1].upper()}{name[1:]}"
            ingredients.append(f"{line} ({measure})" if measure else line)
    return {
        "ext_id": m.get("idMeal"),
        "name": (m.get("strMeal") or "").strip(),
        "category": m.get("strCategory") or "",
        "area": m.get("strArea") or "",
        "image": m.get("strMealThumb") or "",
        "url": m.get("strSource") or (f"https://www.themealdb.com/meal/{m['idMeal']}" if m.get("idMeal") else ""),
        "ingredients": ingredients,
    }


class MealIdeas:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport  # tests pass a mock transport

    async def _get(self, client: httpx.AsyncClient, path: str, **params) -> list[dict]:
        resp = await client.get(f"{BASE}/{path}", params=params)
        resp.raise_for_status()
        return resp.json().get("meals") or []

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=10, transport=self.transport)

    async def random(self, count: int = 4) -> list[dict]:
        """`count` different random dinner ideas."""
        try:
            async with self._client() as client:
                ideas: dict[str, dict] = {}
                for _ in range(3):  # a few rounds in case of repeats or skipped categories
                    batch = await asyncio.gather(*(self._get(client, "random.php") for _ in range(count + 2)))
                    for meals in batch:
                        for m in meals:
                            if m.get("strCategory") not in SKIP_CATEGORIES:
                                ideas.setdefault(m["idMeal"], shape(m))
                    if len(ideas) >= count:
                        break
        except (httpx.HTTPError, ValueError) as exc:
            raise IdeasError("Couldn't reach TheMealDB for ideas. Check the internet connection.") from exc
        return list(ideas.values())[:count]

    async def search(self, query: str, limit: int = 12) -> list[dict]:
        """Meals whose name contains `query`, then meals that use it as the main ingredient."""
        try:
            async with self._client() as client:
                found = await self._get(client, "search.php", s=query)
                ideas = {m["idMeal"]: shape(m) for m in found}
                if len(ideas) < limit:
                    by_ingredient = await self._get(client, "filter.php", i=query.replace(" ", "_"))
                    ids = [m["idMeal"] for m in by_ingredient if m["idMeal"] not in ideas][: limit - len(ideas)]
                    full = await asyncio.gather(*(self._get(client, "lookup.php", i=i) for i in ids))
                    for meals in full:
                        for m in meals:
                            ideas.setdefault(m["idMeal"], shape(m))
        except (httpx.HTTPError, ValueError) as exc:
            raise IdeasError("Couldn't reach TheMealDB for ideas. Check the internet connection.") from exc
        return list(ideas.values())[:limit]
