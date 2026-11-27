"""Google Photos shared album as a slideshow source, read from its public share link.

Since 2025 Google's Photos API can't read existing or shared albums any more, so this reads the
same public web page anyone with the link sees. About once a day it fetches the album page (and the
follow-on pages Google's own page loads as you scroll) and keeps ONLY the list of photo addresses
(text, about 150 bytes each). No photos are downloaded or stored: the wall loads each photo straight
from Google when it's about to show it.

This isn't an official Google API, so Google can change the page at any time. When a check fails
the last good list is kept, and if there has never been one the slideshow just uses the photos
uploaded to the wall.

Anyone with the share link can see the album: that's how Google's link sharing works.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

log = logging.getLogger("family-calendar.album")

LINK_KEY = "album_link"
BATCH_URL = "https://photos.google.com/_/PhotosUi/data/batchexecute"
RPC_ID = "snAcKc"  # the call Google's album page makes to load the next page of photos
CHECK_EVERY = 24 * 3600  # seconds between automatic checks
RETRY_AFTER = 3 * 3600  # after a failed check, try again sooner than a day
MANUAL_GAP = 60  # "Check now" at most once a minute
PAGE_PAUSE = 1.0  # seconds between follow-on pages, to be gentle
MAX_PAGES = 400  # about 120,000 photos; stops a runaway loop if the page format changes
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
PHOTO_URL = re.compile(r"^https://lh3\.googleusercontent\.com/pw/[A-Za-z0-9_\-]+$")
SHARE_PATH = re.compile(r"^/share/([A-Za-z0-9_\-]+)/?$")
LINK_OK = re.compile(
    r"^https://(photos\.app\.goo\.gl/[A-Za-z0-9]+|goo\.gl/photos/[A-Za-z0-9]+|photos\.google\.com/share/[A-Za-z0-9_\-]+\?key=[A-Za-z0-9_\-]+)/?$"
)


class AlbumError(Exception):
    pass


def clean_link(text: str) -> str:
    """The share link from whatever was pasted (Google's share text sometimes has words around it)."""
    m = re.search(r"https://\S+", text or "")
    link = (m.group(0) if m else "").rstrip(".,)")
    if not LINK_OK.match(link):
        raise AlbumError("That doesn't look like a Google Photos album link (it should start with https://photos.app.goo.gl/)")
    return link


class Album:
    def __init__(self, db, data_dir: Path, transport: httpx.AsyncBaseTransport | None = None, pause: float = PAGE_PAUSE):
        self.db = db
        self.file = data_dir / "album.json"
        self._transport = transport
        self._pause = pause
        self.items: list[str] = []  # photo base addresses; the wall adds a size like =w1920-h1080
        self.fetched_at: str | None = None  # last good list
        self.checked_at: float = 0  # last attempt (time.time())
        self.error: str | None = None
        self.checking = False
        self._deck: list[int] = []
        self._lock = asyncio.Lock()
        self.on_change = None
        self._load()

    # --- saved list ------------------------------------------------------------
    @property
    def link(self) -> str:
        return self.db.get_meta(LINK_KEY) or ""

    def _load(self) -> None:
        try:
            data = json.loads(self.file.read_text())
        except (OSError, ValueError):
            return
        if data.get("link") != self.link:
            return  # list belongs to an album that's since been changed or removed
        self.items = [u for u in data.get("items", []) if isinstance(u, str) and PHOTO_URL.match(u)]
        self.fetched_at = data.get("fetched_at")
        self.checked_at = float(data.get("checked_at") or 0)
        self.error = data.get("error")

    def _save(self) -> None:
        tmp = self.file.with_suffix(".part")
        tmp.write_text(json.dumps({
            "link": self.link, "fetched_at": self.fetched_at, "checked_at": self.checked_at,
            "error": self.error, "items": self.items,
        }))
        tmp.replace(self.file)

    def set_link(self, text: str) -> None:
        link = clean_link(text) if text.strip() else ""
        if link == self.link:
            return
        self.db.set_meta(LINK_KEY, link)
        self.items, self._deck, self.fetched_at, self.error, self.checked_at = [], [], None, None, 0
        if link:
            self._save()
        else:
            self.file.unlink(missing_ok=True)
        self._changed()

    def status(self) -> dict:
        return {
            "link": self.link,
            "count": len(self.items),
            "fetched_at": self.fetched_at,
            "checked_at": datetime.fromtimestamp(self.checked_at, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if self.checked_at else None,
            "error": self.error,
            "checking": self.checking,
        }

    def _changed(self) -> None:
        if self.on_change:
            self.on_change()

    # --- picking photos ----------------------------------------------------------
    def draw(self, count: int, uploads: list[str]) -> list[str]:
        """The next few photos for the slideshow, at random from the album and the uploads together.

        Works through a shuffled deck, so no photo comes back until every one has had a turn.
        Returns album addresses (https://...) and upload file names mixed.
        """
        pool = len(self.items) + len(uploads)
        if not pool:
            return []
        out = []
        for _ in range(min(count, pool)):
            if not self._deck:
                self._deck = list(range(pool))
                random.shuffle(self._deck)
            i = self._deck.pop()
            if i >= pool:  # the album or uploads shrank since the deck was dealt
                i = random.randrange(pool)
            out.append(self.items[i] if i < len(self.items) else uploads[i - len(self.items)])
        return out

    # --- checking the album ---------------------------------------------------------
    def due(self) -> bool:
        if not self.link:
            return False
        gap = CHECK_EVERY if self.error is None else RETRY_AFTER
        return time.time() - self.checked_at >= gap

    async def loop(self) -> None:
        """Check the album once a day (sooner after a failure). Runs for the life of the app."""
        while True:
            if self.due():
                await self.refresh()
            await asyncio.sleep(600)

    async def refresh(self, manual: bool = False) -> None:
        if not self.link or self._lock.locked():
            return
        if manual and time.time() - self.checked_at < MANUAL_GAP:
            return
        async with self._lock:
            link = self.link
            self.checking = True
            self._changed()
            try:
                items, problem = await self._fetch(link)
                if link != self.link:
                    return  # changed while we were reading
                if not items:
                    raise AlbumError("Google's page had no photos in it (is the album empty, or has the link been turned off?)")
                if problem and len(items) < len(self.items):
                    raise AlbumError(problem)  # a partial read: the last full list is better
                self.items, self._deck = items, []
                self.fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                self.error = problem
                log.info("album: %d photos%s", len(items), f" ({problem})" if problem else "")
            except Exception as exc:  # keep the last good list
                self.error = str(exc) if isinstance(exc, AlbumError) else f"Couldn't read the album ({type(exc).__name__})"
                log.warning("album check failed: %s", exc)
            finally:
                self.checking = False
                if link == self.link:
                    self.checked_at = time.time()
                    self._save()
                self._changed()

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=30, follow_redirects=True, transport=self._transport,
            headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8"},
        )

    async def _fetch(self, link: str) -> tuple[list[str], str | None]:
        """(photo addresses, problem). A problem with a later page still returns the photos read so far."""
        async with self._client() as c:
            r = await c.get(link)
            if r.status_code == 404:
                raise AlbumError("Google says that album doesn't exist (was link sharing turned off?)")
            if r.status_code != 200:
                raise AlbumError(f"Google answered {r.status_code} for the album page")
            final = urlparse(str(r.url))
            m = SHARE_PATH.match(final.path)
            key = parse_qs(final.query).get("key", [""])[0]
            if final.hostname != "photos.google.com" or not m or not key:
                raise AlbumError("That link didn't open a shared album")
            album_id = m.group(1)
            items, token = parse_album_page(r.text)
            seen = set(items)
            pages = 0
            while token and pages < MAX_PAGES:
                pages += 1
                await asyncio.sleep(self._pause)
                try:
                    more, token = await self._next_page(c, album_id, key, token, final.path)
                except Exception as exc:
                    log.warning("album page %d failed: %s", pages + 1, exc)
                    problem = exc if isinstance(exc, AlbumError) else f"couldn't load more ({type(exc).__name__})"
                    return items, f"Read {len(items):,} photos, then stopped: {problem}"
                fresh = [u for u in more if u not in seen]
                if not fresh:
                    break
                seen.update(fresh)
                items += fresh
            return items, None

    async def _next_page(self, c: httpx.AsyncClient, album_id: str, key: str, token: str, path: str) -> tuple[list[str], str | None]:
        req = json.dumps([[[RPC_ID, json.dumps([album_id, token, None, key]), None, "generic"]]])
        r = await c.post(
            BATCH_URL,
            params={"rpcids": RPC_ID, "source-path": path, "hl": "en", "rt": "c"},
            data={"f.req": req},
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        if r.status_code != 200:
            raise AlbumError(f"Google answered {r.status_code} while loading more")
        return parse_batch(r.text)


# --- reading Google's page format -----------------------------------------------------
def _photos_in(data) -> tuple[list[str], str | None]:
    """[_, [[id, [url, w, h, ...], ...], ...], next page token, ...] -> (urls, token)."""
    if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
        return [], None
    urls = []
    for item in data[1]:
        try:
            url = item[1][0]
        except (TypeError, IndexError, KeyError):
            continue
        if isinstance(url, str) and PHOTO_URL.match(url):
            urls.append(url)
    token = data[2] if len(data) > 2 and isinstance(data[2], str) and data[2] else None
    return urls, token


def parse_album_page(html: str) -> tuple[list[str], str | None]:
    """Photo addresses and the next-page token from a shared album's web page."""
    for m in re.finditer(r"AF_initDataCallback\(\{key: '(ds:\d+)'", html):
        start = html.find("data:", m.end())
        if start < 0:
            continue
        try:
            data, _ = json.JSONDecoder().raw_decode(html, start + 5)
        except ValueError:
            continue
        urls, token = _photos_in(data)
        if urls:
            return urls, token
    # Format changed? Fall back to any album photo addresses on the page (first page only).
    urls = list(dict.fromkeys(re.findall(r"https://lh3\.googleusercontent\.com/pw/[A-Za-z0-9_\-]+", html)))
    return urls, None


def parse_batch(text: str) -> tuple[list[str], str | None]:
    """Google's batchexecute answer: )]}' then lines of JSON, one of them ["wrb.fr", RPC_ID, "<json>", ...]."""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            rows = json.loads(line)
        except ValueError:
            continue
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, list) and len(row) > 2 and row[0] == "wrb.fr" and row[1] == RPC_ID and isinstance(row[2], str):
                try:
                    return _photos_in(json.loads(row[2]))
                except ValueError:
                    pass
    raise AlbumError("Google's page format has changed, so only part of the album could be read")
