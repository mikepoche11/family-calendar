"""Photo screensaver: photos chosen with the Google Photos Picker, plus any images dropped in the folder.

Since March 2025 Google lets apps read only the photos a person explicitly picks, through the
Picker API. Flow:

1. One-time sign-in (OAuth, scope photospicker.mediaitems.readonly). The refresh token is kept in
   the database so later picks don't need another sign-in.
2. "Choose photos" creates a picker session; the person opens its link (QR code on the wall, or
   directly) on a device signed in to that Google account and picks photos.
3. We poll the session; once photos are picked we download copies (max 2048 px) into
   DATA_DIR/photos and delete the session. Google's download links expire after an hour, which is
   why we keep copies instead of hotlinking.

Images copied into DATA_DIR/photos by hand (jpg, jpeg, png, webp) show in the slideshow too.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from .db import Database

log = logging.getLogger("family-calendar.photos")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PICKER_API = "https://photospicker.googleapis.com/v1"
SCOPE = "https://www.googleapis.com/auth/photospicker.mediaitems.readonly"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXT = {".mp4", ".webm"}
MEDIA_EXT = IMAGE_EXT | VIDEO_EXT
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]{1,200}$")
REFRESH_TOKEN_KEY = "google_photos_refresh_token"
MAX_SIDE = 2048  # longest side kept for uploads and Google picks; plenty for a 27" screen
MAX_UPLOAD = 40 * 1024 * 1024
MAX_VIDEO = 500 * 1024 * 1024  # about 4 minutes of 1080p from a phone; the wall plays only the first minute
Image.MAX_IMAGE_PIXELS = 100_000_000  # refuse absurd images instead of using all the memory


class PhotosError(Exception):
    pass


class Photos:
    def __init__(
        self,
        db: Database,
        photos_dir: Path,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.db = db
        self.dir = photos_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._transport = transport
        self._states: dict[str, float] = {}
        self._access: tuple[str, float] | None = None  # (token, expires at monotonic)
        self.pick: dict = {"state": "idle"}  # idle | waiting | downloading | done | error
        self._pick_task: asyncio.Task | None = None

    # --- status ------------------------------------------------------------
    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def connected(self) -> bool:
        return bool(self.db.get_meta(REFRESH_TOKEN_KEY))

    def list(self) -> list[str]:
        files = [p for p in self.dir.iterdir() if p.is_file() and p.suffix.lower() in MEDIA_EXT]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [p.name for p in files if SAFE_NAME.match(p.name)]

    def path_for(self, name: str) -> Path | None:
        if not SAFE_NAME.match(name):
            return None
        p = self.dir / name
        return p if p.is_file() and p.suffix.lower() in MEDIA_EXT else None

    def delete(self, name: str) -> bool:
        p = self.path_for(name)
        if p is None:
            return False
        p.unlink()
        return True

    def delete_all(self) -> int:
        names = self.list()
        for n in names:
            (self.dir / n).unlink(missing_ok=True)
        return len(names)

    def save_upload(self, data: bytes) -> tuple[str, bool]:
        """Store a photo sent from a phone or computer. Returns (file name, newly added).

        The photo is turned upright (phones store rotation separately), shrunk to MAX_SIDE and saved
        as JPEG, which also drops location and camera details. The same photo uploaded twice is kept once.
        """
        if not data:
            raise PhotosError("That file is empty")
        if len(data) > MAX_UPLOAD:
            raise PhotosError("That photo is too big (40 MB max)")
        try:
            with Image.open(io.BytesIO(data)) as img:
                img = ImageOps.exif_transpose(img)
                img.thumbnail((MAX_SIDE, MAX_SIDE))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                out = io.BytesIO()
                img.save(out, "JPEG", quality=88, optimize=True)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise PhotosError("That isn't a photo this screen can show (use JPG, PNG or WebP)")
        name = "up-" + hashlib.sha1(data).hexdigest()[:16] + ".jpg"
        path = self.dir / name
        if path.exists():
            return name, False
        tmp = path.with_suffix(".part")
        tmp.write_bytes(out.getvalue())
        tmp.replace(path)
        return name, True

    def save_video(self, tmp: Path, head: bytes) -> tuple[str, bool]:
        """Keep an uploaded video (already streamed to tmp) as-is. Returns (file name, newly added).

        Phones' normal MP4 (H.264) plays in the wall's browser. HEVC ("high efficiency") clips often
        don't on Linux, so those are turned away with a message rather than showing up blank.
        """
        kind = video_kind(head)
        if kind is None:
            tmp.unlink(missing_ok=True)
            raise PhotosError("That video type can't play on the screen (use MP4)")
        digest = hashlib.sha1()
        hevc = False
        tail = b""
        with tmp.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                digest.update(chunk)
                if kind == "mp4" and not hevc:
                    hevc = b"hvc1" in tail + chunk or b"hev1" in tail + chunk
                    tail = chunk[-8:]
        if hevc:
            tmp.unlink(missing_ok=True)
            raise PhotosError(
                "That video was recorded in high-efficiency (HEVC) format, which the wall can't play. "
                "Turn off the HEVC / high-efficiency video setting in your phone's camera for future clips"
            )
        name = "vid-" + digest.hexdigest()[:16] + "." + kind
        path = self.dir / name
        if path.exists():
            tmp.unlink(missing_ok=True)
            return name, False
        tmp.replace(path)
        return name, True

    def status(self) -> dict:
        return {
            "configured": self.configured,
            "connected": self.connected,
            "count": len(self.list()),
            "pick": self.pick,
        }

    # --- OAuth -------------------------------------------------------------
    def auth_url(self) -> str:
        if not self.configured:
            raise PhotosError("Google Photos isn't set up: add GOOGLE_OAUTH_CLIENT_ID and _SECRET to .env")
        now = time.monotonic()
        self._states = {s: t for s, t in self._states.items() if now - t < 600}
        state = secrets.token_urlsafe(24)
        self._states[state] = now
        return AUTH_URL + "?" + urlencode({
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        })

    async def finish_auth(self, code: str, state: str) -> None:
        if self._states.pop(state, None) is None:
            raise PhotosError("Sign-in link expired; try again")
        data = await self._token({
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        })
        if not data.get("refresh_token"):
            raise PhotosError("Google didn't return a refresh token; remove the app's access in your Google account and retry")
        self.db.set_meta(REFRESH_TOKEN_KEY, data["refresh_token"])
        self._access = (data["access_token"], time.monotonic() + data.get("expires_in", 3600) - 60)

    def disconnect(self) -> None:
        self.db.set_meta(REFRESH_TOKEN_KEY, "")
        self._access = None

    async def _token(self, fields: dict) -> dict:
        async with self._client() as c:
            r = await c.post(TOKEN_URL, data=fields | {"client_id": self.client_id, "client_secret": self.client_secret})
        if r.status_code != 200:
            raise PhotosError(f"Google sign-in failed ({r.status_code}): {r.text[:200]}")
        return r.json()

    async def _access_token(self) -> str:
        if self._access and time.monotonic() < self._access[1]:
            return self._access[0]
        refresh = self.db.get_meta(REFRESH_TOKEN_KEY)
        if not refresh:
            raise PhotosError("Not connected to Google Photos")
        try:
            data = await self._token({"refresh_token": refresh, "grant_type": "refresh_token"})
        except PhotosError:
            self.disconnect()  # token revoked or expired: ask for a fresh sign-in
            raise PhotosError("Google Photos sign-in expired; connect again")
        self._access = (data["access_token"], time.monotonic() + data.get("expires_in", 3600) - 60)
        return self._access[0]

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=30, transport=self._transport)

    async def _api(self, method: str, path: str, **kw) -> dict:
        token = await self._access_token()
        async with self._client() as c:
            r = await c.request(method, PICKER_API + path, headers={"Authorization": f"Bearer {token}"}, **kw)
        if r.status_code >= 400:
            raise PhotosError(f"Google Photos error ({r.status_code}): {r.text[:200]}")
        return r.json() if r.content else {}

    # --- picking -------------------------------------------------------------
    async def start_pick(self) -> dict:
        if self.pick.get("state") in ("waiting", "downloading"):
            return self.pick
        session = await self._api("POST", "/sessions", json={})
        self.pick = {
            "state": "waiting",
            "picker_uri": session["pickerUri"],
            "added": 0,
            "error": None,
        }
        self._pick_task = asyncio.create_task(self._follow(session))
        return self.pick

    def cancel_pick(self) -> None:
        if self._pick_task and not self._pick_task.done():
            self._pick_task.cancel()
        self.pick = {"state": "idle"}

    async def _follow(self, session: dict) -> None:
        sid = session["id"]
        poll = _seconds(session.get("pollingConfig", {}).get("pollInterval"), 3)
        deadline = time.monotonic() + _seconds(session.get("pollingConfig", {}).get("timeoutIn"), 1800)
        try:
            while not session.get("mediaItemsSet"):
                if time.monotonic() > deadline:
                    raise PhotosError("Nobody picked photos in time; try again")
                await asyncio.sleep(max(poll, 1))
                session = await self._api("GET", f"/sessions/{sid}")
            self.pick["state"] = "downloading"
            added = await self._download_all(sid)
            self.pick.update(state="done", added=added)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("photo pick failed")
            self.pick.update(state="error", error=str(exc))
        finally:
            try:
                await self._api("DELETE", f"/sessions/{sid}")
            except Exception:
                pass

    async def _download_all(self, sid: str) -> int:
        added = 0
        page_token = None
        while True:
            params = {"sessionId": sid, "pageSize": 100}
            if page_token:
                params["pageToken"] = page_token
            page = await self._api("GET", "/mediaItems", params=params)
            for item in page.get("mediaItems", []):
                if item.get("type") != "PHOTO":
                    continue  # videos are skipped for now
                name = _file_name(item)
                if (self.dir / name).exists():
                    continue
                token = await self._access_token()
                async with self._client() as c:
                    r = await c.get(item["mediaFile"]["baseUrl"] + "=w2048-h2048", headers={"Authorization": f"Bearer {token}"})
                if r.status_code == 200:
                    (self.dir / name).write_bytes(r.content)
                    added += 1
                    self.pick["added"] = added
            page_token = page.get("nextPageToken")
            if not page_token:
                return added


def video_kind(head: bytes) -> str | None:
    """'mp4' or 'webm' from a file's first bytes, else None."""
    if len(head) >= 12 and head[4:8] == b"ftyp" and head[8:12] not in (b"qt  ", b"heic", b"heix", b"mif1", b"avif"):
        return "mp4"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return None


def _seconds(value: str | None, default: float) -> float:
    """Google durations look like '3.5s'."""
    try:
        return float(str(value).rstrip("s"))
    except (TypeError, ValueError):
        return default


def _file_name(item: dict) -> str:
    mime = item.get("mediaFile", {}).get("mimeType", "image/jpeg")
    ext = {"image/png": ".png", "image/webp": ".webp"}.get(mime, ".jpg")
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", item["id"])[:120]
    return f"gp-{safe_id}{ext}"
