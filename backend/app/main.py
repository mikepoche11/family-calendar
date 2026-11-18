"""Family calendar backend: syncs the shared Google calendar into SQLite and serves the wall UI."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .db import Database
from .demo import demo_events
from .events import from_google, match_person, titled_for, to_google, to_utc_iso
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
        self.weather = Weather(settings.latitude, settings.longitude, settings.timezone, settings.temperature_unit)
        self.broadcaster = Broadcaster()
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
class PersonIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class PersonPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class EventIn(BaseModel):
    summary: str = Field(min_length=1, max_length=200)
    start: str  # "YYYY-MM-DD" for all-day; else ISO datetime (with offset/Z, or local to TIMEZONE if none)
    end: str
    all_day: bool = False
    person_id: int | None = None
    description: str = ""
    location: str = ""


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
    return {"timezone": s.settings.timezone, "mode": "demo" if s.google is None else "google"}


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
        person = s.db.create_person(body.name.strip(), body.color)
    except Exception:
        raise HTTPException(409, "A person with that name already exists")
    _people_changed(s)
    return person


@app.patch("/api/people/{pid}")
def update_person(pid: int, body: PersonPatch, request: Request):
    s = st(request)
    person = s.db.update_person(pid, body.name.strip() if body.name else None, body.color)
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
