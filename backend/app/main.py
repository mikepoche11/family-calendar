"""Family calendar backend: syncs the shared Google calendar into SQLite and serves the wall UI."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .db import Database
from .demo import demo_events
from .events import from_google, match_person, titled_for, to_google, to_utc_iso
from .chores import Chores
from .marbles import MarbleError, Marbles
from .mealdb import IdeasError, MealIdeas
from .meals import Meals, week_start
from .photos import Photos, PhotosError
from .weather import Weather

log = logging.getLogger("family-calendar")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


class Broadcaster:
    """Tells every open wall/phone screen that data changed (Server-Sent Events)."""

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[str]] = set()

    def publish(self, kind: str) -> None:
        for q in list(self._queues):
            q.put_nowait(kind)

    async def subscribe(self):
        q: asyncio.Queue[str] = asyncio.Queue()
        self._queues.add(q)
        try:
            while True:
                try:
                    kind = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"event: changed\ndata: {json.dumps({'kind': kind})}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            self._queues.discard(q)


class State:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.db_path)
        self.db.seed_people(settings.people_seed)
        self.db.pastelize_people()
        self.weather = Weather(settings.latitude, settings.longitude, settings.timezone, settings.temperature_unit)
        self.broadcaster = Broadcaster()
        self.marbles = Marbles(self.db)
        self.chores = Chores(self.db, self.marbles)
        self.meals = Meals(self.db)
        self.ideas = MealIdeas()
        self.photos = Photos(
            self.db,
            settings.photos_dir,
            settings.google_oauth_client_id,
            settings.google_oauth_client_secret,
            settings.public_url + "/api/photos/auth/callback",
        )
        self.google = None
        self.last_sync: str | None = None
        self.last_error: str | None = None
        self.sync_now = asyncio.Event()
        if settings.google_enabled:
            from .google_calendar import GoogleCalendar

            self.google = GoogleCalendar(settings.google_service_account_file, settings.google_calendar_id)

    async def sync_once(self) -> None:
        people = self.db.list_people()
        if self.google is None:
            # Demo mode: (re)write the sample events, keep events added on the screen
            rows = demo_events(people, self.settings.timezone)
            changed = any(self.db.get_event(r["id"]) is None for r in rows)
            for r in rows:
                self.db.upsert_event(r)
        else:
            s = self.settings
            w_start, w_end, items = await asyncio.to_thread(self.google.list_window, s.sync_days_back, s.sync_days_ahead)
            rows = [r for r in (from_google(i, people) for i in items) if r]
            changed = self.db.replace_window(w_start, w_end, rows)
        self.last_sync = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.last_error = None
        if changed:
            log.info("calendar changed: %d events in window", len(rows))
            self.broadcaster.publish("events")

    async def sync_loop(self) -> None:
        while True:
            try:
                await self.sync_once()
            except Exception as exc:  # keep the wall running; show the error in /api/health
                self.last_error = f"{type(exc).__name__}: {exc}"
                log.exception("sync failed")
            self.sync_now.clear()
            try:
                await asyncio.wait_for(self.sync_now.wait(), timeout=self.settings.sync_interval_seconds)
            except asyncio.TimeoutError:
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = State(get_settings())
    app.state.s = state
    log.info("starting in %s mode", "demo" if state.google is None else "google")
    task = asyncio.create_task(state.sync_loop())
    yield
    task.cancel()


app = FastAPI(title="Family Calendar", lifespan=lifespan)


def st(request: Request) -> State:
    return request.app.state.s


# --- models ------------------------------------------------------------------
AVATAR = r"^[a-z0-9-]{0,32}$"  # id of a built-in avatar (frontend/src/avatars.jsx); "" = initial letter


class PersonIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    avatar: str = Field(default="", pattern=AVATAR)


class PersonPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    avatar: str | None = Field(default=None, pattern=AVATAR)


class GroceryIn(BaseModel):
    text: str = Field(min_length=1, max_length=120)


class GroceryPatch(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=120)
    done: bool | None = None


class GroceryLine(BaseModel):
    text: str = Field(max_length=200)
    days: list[Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]] = Field(default_factory=list, max_length=14)  # dinner nights it's for


class GroceryBulk(BaseModel):
    # Plain strings are hand-picked lines; GroceryLine ties a line to dinner nights so clearing them removes it
    items: list[str | GroceryLine] = Field(max_length=100)


DAYS = r"^[0-6]{1,7}$"


class ChoreIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    icon: str = Field(default="", max_length=32)
    person_id: int | None = None  # None = anyone
    days: str = Field(default="0123456", pattern=DAYS)  # Monday = 0
    marbles: int = Field(default=0, ge=0, le=20)  # blue marbles earned when done


class ChorePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    icon: str | None = Field(default=None, max_length=32)
    person_id: int | None = None
    anyone: bool = False  # set to make the chore "anyone" (person_id null)
    days: str | None = Field(default=None, pattern=DAYS)
    marbles: int | None = Field(default=None, ge=0, le=20)


class ChoreDone(BaseModel):
    done: bool
    person_id: int | None = None  # who did an "anyone" chore


class StarterIn(BaseModel):
    kid_ids: list[int]


class JarsIn(BaseModel):
    person_ids: list[int]


class MarbleAdd(BaseModel):
    color: str = Field(pattern=r"^(blue|white)$")
    count: int = Field(default=1, ge=1, le=20)


class SpendIn(BaseModel):
    reward_id: int


class RewardIn(BaseModel):
    title: str = Field(min_length=1, max_length=40)
    icon: str = Field(default="", max_length=32)
    cost: int = Field(ge=1, le=100)


class RewardPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=40)
    icon: str | None = Field(default=None, max_length=32)
    cost: int | None = Field(default=None, ge=1, le=100)


class MealIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    icon: str = Field(default="", max_length=32)
    ingredients: list[str] = Field(default_factory=list, max_length=40)
    url: str = Field(default="", max_length=500)
    image: str = Field(default="", max_length=500)


class MealPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    icon: str | None = Field(default=None, max_length=32)
    ingredients: list[str] | None = Field(default=None, max_length=40)
    url: str | None = Field(default=None, max_length=500)
    image: str | None = Field(default=None, max_length=500)


class PlanDay(BaseModel):
    meal_id: int | None = None  # None clears the night


class EventIn(BaseModel):
    summary: str = Field(min_length=1, max_length=200)
    start: str  # "YYYY-MM-DD" for all-day; else ISO datetime (with offset/Z, or local to TIMEZONE if none)
    end: str
    all_day: bool = False
    person_id: int | None = None
    description: str = ""
    location: str = ""
    color_id: str = Field(default="", pattern=r"^([1-9]|1[01])?$")  # Google event colour; "" = calendar default


# --- health/config -------------------------------------------------------------
@app.get("/api/health")
def health(request: Request):
    s = st(request)
    return {
        "mode": "demo" if s.google is None else "google",
        "last_sync": s.last_sync,
        "last_error": s.last_error,
    }


@app.get("/api/config")
def config(request: Request):
    s = st(request)
    return {
        "timezone": s.settings.timezone,
        "mode": "demo" if s.google is None else "google",
        "screensaver_minutes": s.settings.screensaver_minutes,
        "slide_seconds": s.settings.slide_seconds,
        "theme": s.db.get_meta("theme") or "",
        "theme_backgrounds": _theme_backgrounds(s),
    }


THEME = r"^[a-z0-9-]{0,32}$"  # id of a theme in frontend/src/themes.js; "" = the everyday pastel look


class ThemeIn(BaseModel):
    theme: str = Field(pattern=THEME)


class ThemeBackgroundIn(BaseModel):
    theme: str = Field(pattern=THEME)
    color: str = Field(pattern=r"^(#[0-9a-fA-F]{6})?$")  # "" = back to the theme's own background


def _theme_backgrounds(s) -> dict[str, str]:
    try:
        data = json.loads(s.db.get_meta("theme_backgrounds") or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


@app.put("/api/theme/background")
def set_theme_background(body: ThemeBackgroundIn, request: Request):
    """Custom page background for one theme (e.g. a darker green for Christmas); "" resets it."""
    s = st(request)
    data = _theme_backgrounds(s)
    if body.color:
        data[body.theme] = body.color.lower()
    else:
        data.pop(body.theme, None)
    s.db.set_meta("theme_backgrounds", json.dumps(data, sort_keys=True))
    s.broadcaster.publish("theme")
    return {"theme_backgrounds": data}


@app.put("/api/theme")
def set_theme(body: ThemeIn, request: Request):
    """Whole-app colour theme, shared by the wall screen and every phone."""
    s = st(request)
    s.db.set_meta("theme", body.theme)
    s.broadcaster.publish("theme")
    return {"theme": body.theme}


@app.post("/api/sync")
def trigger_sync(request: Request):
    st(request).sync_now.set()
    return {"ok": True}


# --- people --------------------------------------------------------------------
@app.get("/api/people")
def list_people(request: Request):
    return st(request).db.list_people()


def _people_changed(s: State) -> None:
    s.db.reassign_people(s.db.list_people(), match_person)
    s.broadcaster.publish("people")


@app.post("/api/people", status_code=201)
def create_person(body: PersonIn, request: Request):
    s = st(request)
    try:
        person = s.db.create_person(body.name.strip(), body.color, body.avatar)
    except Exception:
        raise HTTPException(409, "A person with that name already exists")
    _people_changed(s)
    return person


@app.patch("/api/people/{pid}")
def update_person(pid: int, body: PersonPatch, request: Request):
    s = st(request)
    person = s.db.update_person(pid, body.name.strip() if body.name else None, body.color, body.avatar)
    if not person:
        raise HTTPException(404, "No such person")
    _people_changed(s)
    return person


@app.delete("/api/people/{pid}", status_code=204)
def delete_person(pid: int, request: Request):
    s = st(request)
    if not s.db.delete_person(pid):
        raise HTTPException(404, "No such person")
    _people_changed(s)


# --- events --------------------------------------------------------------------
@app.get("/api/events")
def list_events(request: Request, start: str = Query(...), end: str = Query(...)):
    return st(request).db.list_events(start, end)


def _local_to_utc(value: str, tz: str) -> str:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    return to_utc_iso(dt.isoformat())


def _validate_times(body: EventIn) -> None:
    try:
        if body.all_day:
            datetime.strptime(body.start[:10], "%Y-%m-%d")
            datetime.strptime(body.end[:10], "%Y-%m-%d")
            ok = body.end[:10] > body.start[:10]
        else:
            ok = datetime.fromisoformat(body.end) > datetime.fromisoformat(body.start)
    except ValueError:
        raise HTTPException(422, "Dates must be YYYY-MM-DD or YYYY-MM-DDTHH:MM")
    if not ok:
        raise HTTPException(422, "The event must end after it starts")


def _resolve_person(s: State, person_id: int | None) -> tuple[dict | None, list[dict]]:
    people = s.db.list_people()
    if person_id is None:
        return None, people
    person = next((p for p in people if p["id"] == person_id), None)
    if person is None:
        raise HTTPException(422, "Unknown person")
    return person, people


def _local_row(event_id: str, body: EventIn, summary: str, people: list[dict], tz: str) -> dict:
    return {
        "id": event_id,
        "summary": summary,
        "description": body.description,
        "location": body.location,
        "start": body.start[:10] if body.all_day else _local_to_utc(body.start, tz),
        "end": body.end[:10] if body.all_day else _local_to_utc(body.end, tz),
        "all_day": int(body.all_day),
        "person_id": match_person(summary, people),
        "recurring": 0,
        "updated": datetime.now(timezone.utc).isoformat(),
        "color_id": body.color_id,
    }


@app.post("/api/events", status_code=201)
async def create_event(body: EventIn, request: Request):
    s = st(request)
    _validate_times(body)
    person, people = _resolve_person(s, body.person_id)
    summary = titled_for(body.summary.strip(), person, people)
    if s.google is None:
        row = _local_row(f"local-{uuid.uuid4().hex[:12]}", body, summary, people, s.settings.timezone)
    else:
        payload = body.model_dump() | {"summary": summary}
        created = await asyncio.to_thread(s.google.insert, to_google(payload, s.settings.timezone))
        row = from_google(created, people)
    s.db.upsert_event(row)
    s.broadcaster.publish("events")
    return s.db.get_event(row["id"])


@app.patch("/api/events/{event_id}")
async def update_event(event_id: str, body: EventIn, request: Request):
    s = st(request)
    if not s.db.get_event(event_id):
        raise HTTPException(404, "No such event")
    _validate_times(body)
    person, people = _resolve_person(s, body.person_id)
    summary = titled_for(body.summary.strip(), person, people)
    if s.google is None:
        row = _local_row(event_id, body, summary, people, s.settings.timezone)
    else:
        payload = body.model_dump() | {"summary": summary}
        updated = await asyncio.to_thread(s.google.patch, event_id, to_google(payload, s.settings.timezone))
        row = from_google(updated, people)
    s.db.upsert_event(row)
    s.broadcaster.publish("events")
    return s.db.get_event(row["id"])


@app.delete("/api/events/{event_id}", status_code=204)
async def delete_event(event_id: str, request: Request):
    s = st(request)
    if not s.db.get_event(event_id):
        raise HTTPException(404, "No such event")
    if s.google is not None:
        await asyncio.to_thread(s.google.delete, event_id)
    s.db.delete_event(event_id)
    s.broadcaster.publish("events")


# --- grocery list ---------------------------------------------------------------
@app.get("/api/grocery")
def grocery_list(request: Request):
    return st(request).db.list_grocery()


@app.post("/api/grocery", status_code=201)
def grocery_add(body: GroceryIn, request: Request):
    s = st(request)
    text = body.text.strip()
    if not text:
        raise HTTPException(422, "Type something to add")
    item = s.db.add_grocery(text)
    s.broadcaster.publish("grocery")
    return item


@app.patch("/api/grocery/{gid}")
def grocery_update(gid: int, body: GroceryPatch, request: Request):
    s = st(request)
    item = s.db.update_grocery(gid, body.text.strip() if body.text else None, body.done)
    if not item:
        raise HTTPException(404, "No such item")
    s.broadcaster.publish("grocery")
    return item


@app.delete("/api/grocery/{gid}", status_code=204)
def grocery_delete(gid: int, request: Request):
    s = st(request)
    if not s.db.delete_grocery(gid):
        raise HTTPException(404, "No such item")
    s.broadcaster.publish("grocery")


@app.post("/api/grocery/clear-checked")
def grocery_clear_checked(request: Request):
    s = st(request)
    n = s.db.clear_checked_grocery()
    s.broadcaster.publish("grocery")
    return {"deleted": n}


@app.post("/api/grocery/bulk")
def grocery_bulk(body: GroceryBulk, request: Request):
    """Add several lines at once (a meal's ingredients); skips things already on the list."""
    s = st(request)
    lines = [t if isinstance(t, str) else (t.text, t.days) for t in body.items]
    result = s.db.add_grocery_lines([t for t in lines if (t if isinstance(t, str) else t[0]).strip()])
    if result["added"]:
        s.broadcaster.publish("grocery")
    return result


# --- calendar stickers ---------------------------------------------------------------
# Decorations only: saved in the app's database and never sent to Google Calendar.
DAY = r"^\d{4}-\d{2}-\d{2}$"
ICON = r"^[a-z0-9-]{1,32}$"


class StickerIn(BaseModel):
    day: str = Field(pattern=DAY)
    icon: str = Field(pattern=ICON)
    x: float = Field(0.5, ge=-1, le=2)
    y: float = Field(0.5, ge=-1, le=2)
    size: float = Field(0.6, ge=0.1, le=3)
    rotation: float = Field(0, ge=-3600, le=3600)


class StickerPatch(BaseModel):
    day: str | None = Field(None, pattern=DAY)
    x: float | None = Field(None, ge=-1, le=2)
    y: float | None = Field(None, ge=-1, le=2)
    size: float | None = Field(None, ge=0.1, le=3)
    rotation: float | None = Field(None, ge=-3600, le=3600)


def _norm_rotation(deg: float | None) -> float | None:
    return None if deg is None else round(((deg + 180) % 360) - 180, 2)


@app.get("/api/stickers")
def stickers_list(request: Request, start: str | None = Query(None, pattern=DAY), end: str | None = Query(None, pattern=DAY)):
    return st(request).db.list_stickers(start, end)


@app.post("/api/stickers", status_code=201)
def sticker_add(body: StickerIn, request: Request):
    s = st(request)
    sticker = s.db.add_sticker(body.day, body.icon, body.x, body.y, body.size, _norm_rotation(body.rotation))
    s.broadcaster.publish("stickers")
    return sticker


@app.patch("/api/stickers/{sid}")
def sticker_update(sid: int, body: StickerPatch, request: Request):
    s = st(request)
    fields = body.model_dump()
    fields["rotation"] = _norm_rotation(body.rotation)
    sticker = s.db.update_sticker(sid, **fields)
    if not sticker:
        raise HTTPException(404, "No such sticker")
    s.broadcaster.publish("stickers")
    return sticker


@app.delete("/api/stickers/{sid}", status_code=204)
def sticker_delete(sid: int, request: Request):
    s = st(request)
    if not s.db.delete_sticker(sid):
        raise HTTPException(404, "No such sticker")
    s.broadcaster.publish("stickers")


# --- chores -------------------------------------------------------------------------
def _today(s: State):
    return datetime.now(ZoneInfo(s.settings.timezone)).date()


def _check_person(s: State, pid: int | None) -> None:
    if pid is not None and pid not in {p["id"] for p in s.db.list_people()}:
        raise HTTPException(422, "Unknown person")


@app.get("/api/chores")
def chores_list(request: Request):
    return st(request).chores.list()


@app.get("/api/chores/today")
def chores_today(request: Request):
    s = st(request)
    today = _today(s)
    return {"date": today.isoformat(), "chores": s.chores.for_day(today)}


@app.post("/api/chores", status_code=201)
def chores_create(body: ChoreIn, request: Request):
    s = st(request)
    _check_person(s, body.person_id)
    chore = s.chores.create(body.title.strip(), body.icon.strip(), body.person_id, body.days, body.marbles)
    s.broadcaster.publish("chores")
    return chore


@app.patch("/api/chores/{cid}")
def chores_update(cid: int, body: ChorePatch, request: Request):
    s = st(request)
    fields = body.model_dump(exclude_unset=True, exclude={"anyone"})
    if body.anyone:
        fields["person_id"] = None
    elif "person_id" in fields:
        _check_person(s, fields["person_id"])
    if "title" in fields:
        fields["title"] = fields["title"].strip()
    chore = s.chores.update(cid, fields)
    if not chore:
        raise HTTPException(404, "No such chore")
    s.broadcaster.publish("chores")
    return chore


@app.delete("/api/chores/{cid}", status_code=204)
def chores_delete(cid: int, request: Request):
    s = st(request)
    if not s.chores.delete(cid):
        raise HTTPException(404, "No such chore")
    s.broadcaster.publish("chores")


@app.post("/api/chores/{cid}/done")
def chores_done(cid: int, body: ChoreDone, request: Request):
    s = st(request)
    _check_person(s, body.person_id)
    result = s.chores.set_done(cid, _today(s), body.done, body.person_id)
    if result is None:
        raise HTTPException(404, "No such chore")
    s.broadcaster.publish("chores")
    if result["marbles"]:
        s.broadcaster.publish("marbles")
    jars = {j["person_id"]: j for j in s.marbles.jars()}
    for change in result["marbles"]:
        change["jar"] = jars.get(change["person_id"])
    return {"ok": True, **result}


@app.post("/api/chores/starter", status_code=201)
def chores_starter(body: StarterIn, request: Request):
    s = st(request)
    for pid in body.kid_ids:
        _check_person(s, pid)
    n = s.chores.add_starter(body.kid_ids)
    s.broadcaster.publish("chores")
    return {"added": n}


# --- marble jars -----------------------------------------------------------------
def _marbles(s: State, fn):
    try:
        jar = fn()
    except LookupError as e:
        raise HTTPException(404, str(e))
    except MarbleError as e:
        raise HTTPException(409, str(e))
    s.broadcaster.publish("marbles")
    return jar


@app.get("/api/marbles")
def marbles_list(request: Request):
    s = st(request)
    return {"jars": s.marbles.jars(), "rewards": s.marbles.rewards()}


@app.put("/api/marbles/jars")
def marbles_set_jars(body: JarsIn, request: Request):
    s = st(request)
    for pid in body.person_ids:
        _check_person(s, pid)
    s.marbles.set_jars(body.person_ids)
    s.broadcaster.publish("marbles")
    return s.marbles.jars()


@app.delete("/api/marbles/{pid}", status_code=204)
def marbles_remove_jar(pid: int, request: Request):
    s = st(request)
    if not s.marbles.remove_jar(pid):
        raise HTTPException(404, "No such jar")
    s.broadcaster.publish("marbles")


@app.post("/api/marbles/{pid}/add")
def marbles_add(pid: int, body: MarbleAdd, request: Request):
    s = st(request)
    return _marbles(s, lambda: s.marbles.add(pid, body.color, body.count))


@app.post("/api/marbles/{pid}/spend")
def marbles_spend(pid: int, body: SpendIn, request: Request):
    s = st(request)
    return _marbles(s, lambda: s.marbles.spend(pid, body.reward_id))


@app.post("/api/marbles/{pid}/cancel")
def marbles_cancel(pid: int, request: Request):
    s = st(request)
    return _marbles(s, lambda: s.marbles.cancel(pid))


@app.post("/api/marbles/{pid}/undo")
def marbles_undo(pid: int, request: Request):
    s = st(request)
    return _marbles(s, lambda: s.marbles.undo(pid))


@app.get("/api/marbles/{pid}/history")
def marbles_history(pid: int, request: Request):
    return st(request).marbles.history(pid)


@app.post("/api/rewards", status_code=201)
def rewards_create(body: RewardIn, request: Request):
    s = st(request)
    r = s.marbles.create_reward(body.title.strip(), body.icon.strip(), body.cost)
    s.broadcaster.publish("marbles")
    return r


@app.patch("/api/rewards/{rid}")
def rewards_update(rid: int, body: RewardPatch, request: Request):
    s = st(request)
    fields = body.model_dump(exclude_unset=True, exclude_none=True)
    if "title" in fields:
        fields["title"] = fields["title"].strip()
    r = s.marbles.update_reward(rid, fields)
    if not r:
        raise HTTPException(404, "No such reward")
    s.broadcaster.publish("marbles")
    return r


@app.delete("/api/rewards/{rid}", status_code=204)
def rewards_delete(rid: int, request: Request):
    s = st(request)
    if not s.marbles.delete_reward(rid):
        raise HTTPException(404, "No such reward")
    s.broadcaster.publish("marbles")


# --- meals ------------------------------------------------------------------------
def _parse_day(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(422, "Dates must be YYYY-MM-DD")


def _check_url(url: str | None) -> None:
    if url and not url.startswith(("http://", "https://")):
        raise HTTPException(422, "Links must start with http:// or https://")


@app.get("/api/meals")
def meals_list(request: Request):
    return st(request).meals.list()


@app.post("/api/meals", status_code=201)
def meals_create(body: MealIn, request: Request):
    s = st(request)
    _check_url(body.url)
    _check_url(body.image)
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Give the meal a name")
    meal = s.meals.create(name, body.icon.strip(), body.ingredients, body.url.strip(), body.image.strip())
    s.broadcaster.publish("meals")
    return meal


@app.patch("/api/meals/{mid}")
def meals_update(mid: int, body: MealPatch, request: Request):
    s = st(request)
    fields = body.model_dump(exclude_unset=True, exclude_none=True)
    _check_url(fields.get("url"))
    _check_url(fields.get("image"))
    for k in ("name", "icon", "url"):
        if k in fields:
            fields[k] = fields[k].strip()
    if fields.get("name") == "":
        raise HTTPException(422, "Give the meal a name")
    if not s.meals.get(mid):
        raise HTTPException(404, "No such meal")
    try:
        meal = s.meals.update(mid, fields)
    except Exception:
        raise HTTPException(409, "There's already a meal with that name")
    s.broadcaster.publish("meals")
    return meal


@app.delete("/api/meals/{mid}", status_code=204)
def meals_delete(mid: int, request: Request):
    s = st(request)
    if not s.meals.delete(mid):
        raise HTTPException(404, "No such meal")
    s.broadcaster.publish("meals")
    s.broadcaster.publish("grocery")


@app.post("/api/meals/starter", status_code=201)
def meals_starter(request: Request):
    s = st(request)
    n = s.meals.add_starter()
    s.broadcaster.publish("meals")
    return {"added": n}


@app.get("/api/meals/ideas")
async def meals_ideas(request: Request, q: str = ""):
    s = st(request)
    q = q.strip()[:60]
    try:
        ideas = await (s.ideas.search(q) if q else s.ideas.random())
    except IdeasError as exc:
        raise HTTPException(503, str(exc))
    return {"ideas": ideas}


@app.get("/api/meal-plan")
def meal_plan(request: Request, start: str = ""):
    s = st(request)
    today = _today(s)
    first = week_start(_parse_day(start) if start else today)
    return {"start": first.isoformat(), "today": today.isoformat(), "days": s.meals.week(first)}


@app.put("/api/meal-plan/{day}")
def meal_plan_set(day: str, body: PlanDay, request: Request):
    s = st(request)
    removed = s.meals.set_day(_parse_day(day), body.meal_id)
    if removed is None:
        raise HTTPException(404, "No such meal")
    s.broadcaster.publish("meals")
    if removed:
        s.broadcaster.publish("grocery")
    return {"ok": True, "removed": removed}


@app.post("/api/meal-plan/fill")
def meal_plan_fill(request: Request, start: str = ""):
    s = st(request)
    first = week_start(_parse_day(start) if start else _today(s))
    n = s.meals.fill_week(first)
    s.broadcaster.publish("meals")
    return {"filled": n}


# --- photos ---------------------------------------------------------------------
@app.get("/api/photos")
def photos_list(request: Request):
    return st(request).photos.list()


@app.get("/api/photos/status")
def photos_status(request: Request):
    return st(request).photos.status()


@app.get("/api/photos/file/{name}")
def photos_file(name: str, request: Request):
    path = st(request).photos.path_for(name)
    if path is None:
        raise HTTPException(404, "No such photo")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@app.delete("/api/photos/file/{name}", status_code=204)
def photos_delete(name: str, request: Request):
    s = st(request)
    if not s.photos.delete(name):
        raise HTTPException(404, "No such photo")
    s.broadcaster.publish("photos")


@app.delete("/api/photos")
def photos_delete_all(request: Request):
    s = st(request)
    n = s.photos.delete_all()
    s.broadcaster.publish("photos")
    return {"deleted": n}


@app.get("/api/photos/auth/start", include_in_schema=False)
def photos_auth_start(request: Request):
    try:
        return RedirectResponse(st(request).photos.auth_url())
    except PhotosError as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/photos/auth/callback", include_in_schema=False)
async def photos_auth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    s = st(request)
    if error:
        return RedirectResponse(f"/?photos_error={error}")
    try:
        await s.photos.finish_auth(code, state)
    except PhotosError as exc:
        return RedirectResponse(f"/?photos_error={exc}")
    s.broadcaster.publish("photos")
    return RedirectResponse("/?photos=connected")


@app.post("/api/photos/disconnect")
def photos_disconnect(request: Request):
    st(request).photos.disconnect()
    return {"ok": True}


@app.post("/api/photos/pick")
async def photos_pick(request: Request):
    s = st(request)
    try:
        pick = await s.photos.start_pick()
    except PhotosError as exc:
        raise HTTPException(400, str(exc))
    return pick


@app.delete("/api/photos/pick")
def photos_pick_cancel(request: Request):
    st(request).photos.cancel_pick()
    return {"ok": True}


# --- weather + live updates -------------------------------------------------------
@app.get("/api/weather")
async def weather(request: Request):
    return await st(request).weather.get()


@app.get("/api/stream")
async def stream(request: Request):
    return StreamingResponse(
        st(request).broadcaster.subscribe(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- wall UI (built frontend) -------------------------------------------------------
_static = get_settings().static_dir
if (_static / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = (_static / path).resolve()
        if path and candidate.is_file() and _static.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")
