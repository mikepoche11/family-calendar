"""Google Photos Picker flow against a fake Google (httpx.MockTransport)."""

import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.db import Database
from app.photos import Photos, PhotosError

JPEG = b"\xff\xd8\xff\xe0fakejpeg"


class FakeGoogle:
    def __init__(self):
        self.polls = 0
        self.deleted = False
        self.refreshes = 0

    def __call__(self, req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if url.startswith("https://oauth2.googleapis.com/token"):
            form = parse_qs(req.content.decode())
            if form["grant_type"] == ["authorization_code"]:
                assert form["code"] == ["the-code"]
                return httpx.Response(200, json={"access_token": "a1", "refresh_token": "r1", "expires_in": 3600})
            self.refreshes += 1
            return httpx.Response(200, json={"access_token": "a2", "expires_in": 3600})
        assert req.headers.get("authorization", "").startswith("Bearer ")
        if req.method == "POST" and url.endswith("/v1/sessions"):
            return httpx.Response(200, json={
                "id": "s1", "pickerUri": "https://photos.google.com/picker/s1",
                "pollingConfig": {"pollInterval": "0.01s", "timeoutIn": "60s"}, "mediaItemsSet": False,
            })
        if req.method == "GET" and url.endswith("/v1/sessions/s1"):
            self.polls += 1
            return httpx.Response(200, json={"id": "s1", "mediaItemsSet": self.polls >= 2})
        if req.method == "DELETE" and url.endswith("/v1/sessions/s1"):
            self.deleted = True
            return httpx.Response(200, json={})
        if "/v1/mediaItems" in url:
            return httpx.Response(200, json={"mediaItems": [
                {"id": "p/1", "type": "PHOTO", "mediaFile": {"baseUrl": "https://lh3.example/p1", "mimeType": "image/jpeg"}},
                {"id": "v1", "type": "VIDEO", "mediaFile": {"baseUrl": "https://lh3.example/v1", "mimeType": "video/mp4"}},
            ]})
        if url.startswith("https://lh3.example/p1=w2048-h2048"):
            return httpx.Response(200, content=JPEG)
        return httpx.Response(404)


@pytest.fixture()
def setup(tmp_path):
    google = FakeGoogle()
    photos = Photos(
        Database(tmp_path / "db.sqlite"), tmp_path / "photos", "cid", "secret",
        "http://localhost:8000/api/photos/auth/callback", transport=httpx.MockTransport(google),
    )
    return photos, google


def test_not_configured(tmp_path):
    p = Photos(Database(tmp_path / "db.sqlite"), tmp_path / "photos", "", "", "http://x/cb")
    with pytest.raises(PhotosError):
        p.auth_url()


def test_auth_pick_and_download(setup):
    photos, google = setup
    url = urlparse(photos.auth_url())
    q = parse_qs(url.query)
    assert q["scope"] == ["https://www.googleapis.com/auth/photospicker.mediaitems.readonly"]
    assert q["access_type"] == ["offline"]

    async def flow():
        with pytest.raises(PhotosError):
            await photos.finish_auth("the-code", "wrong-state")
        await photos.finish_auth("the-code", q["state"][0])
        assert photos.connected
        pick = await photos.start_pick()
        assert pick["picker_uri"] == "https://photos.google.com/picker/s1"
        await photos._pick_task

    asyncio.run(flow())
    assert photos.pick["state"] == "done" and photos.pick["added"] == 1
    assert photos.list() == ["gp-p1.jpg"]  # video skipped, id sanitised
    assert photos.path_for("gp-p1.jpg").read_bytes() == JPEG
    assert google.deleted


def test_state_is_single_use(setup):
    photos, _ = setup
    state = parse_qs(urlparse(photos.auth_url()).query)["state"][0]
    asyncio.run(photos.finish_auth("the-code", state))
    with pytest.raises(PhotosError):
        asyncio.run(photos.finish_auth("the-code", state))


def test_local_files_and_safe_names(setup):
    photos, _ = setup
    (photos.dir / "beach.JPG").write_bytes(JPEG)
    (photos.dir / "notes.txt").write_text("x")
    assert photos.list() == ["beach.JPG"]
    assert photos.path_for("../db.sqlite") is None
    assert photos.path_for("notes.txt") is None
    assert photos.delete("beach.JPG") and photos.list() == []
