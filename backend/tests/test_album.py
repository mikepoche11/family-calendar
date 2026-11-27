"""Shared Google Photos album, read from its share link against a fake Google (httpx.MockTransport)."""

import asyncio
import json
from urllib.parse import parse_qs

import httpx
import pytest

from app.album import Album, AlbumError, clean_link, parse_album_page, parse_batch
from app.db import Database

LINK = "https://photos.app.goo.gl/AbC123xyz"
SHARE = "https://photos.google.com/share/ALBUM1?key=KEY1"


def url(n):
    return f"https://lh3.googleusercontent.com/pw/PHOTO{n}"


def item(n):
    return [f"id{n}", [url(n), 4032, 3024, None, None, None, None, None, None, [1]], 1700000000000 + n, "x", -21600000]


def page_html(urls_from, urls_to, token):
    data = [None, [item(n) for n in range(urls_from, urls_to)], token, None, ["album info"]]
    owner = "https://lh3.googleusercontent.com/a/OWNERAVATAR"
    return (
        f'<html><img src="{owner}"><script nonce="n">AF_initDataCallback({{key: \'ds:0\', hash: \'1\', data:[1,2], sideChannel: {{}}}});</script>'
        f"<script nonce=\"n\">AF_initDataCallback({{key: 'ds:1', hash: '2', data:{json.dumps(data)}, sideChannel: {{}}}});</script></html>"
    )


def batch_text(urls_from, urls_to, token):
    inner = json.dumps([None, [item(n) for n in range(urls_from, urls_to)], token])
    row = json.dumps([["wrb.fr", "snAcKc", inner, None, None, None, "generic"], ["di", 50]])
    return f")]}}'\n\n{len(row)}\n{row}\n25\n[[\"e\",4,null,null,123]]\n"


class FakeGoogle:
    """Album of 7 photos: 3 on the page, then pages of 2 by token."""

    def __init__(self):
        self.pages = {"T1": (3, 5, "T2"), "T2": (5, 7, None)}
        self.fail_page = None
        self.calls = 0
        self.down = False

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self.down:
            return httpx.Response(503)
        u = str(req.url)
        if u == LINK:
            return httpx.Response(302, headers={"Location": SHARE})
        if u == SHARE:
            return httpx.Response(200, text=page_html(0, 3, "T1"))
        if u.startswith("https://photos.google.com/_/PhotosUi/data/batchexecute"):
            assert req.method == "POST"
            assert "rpcids=snAcKc" in u
            f_req = json.loads(parse_qs(req.content.decode())["f.req"][0])
            rpc, args, _, _ = f_req[0][0]
            assert rpc == "snAcKc"
            album_id, token, _, key = json.loads(args)
            assert (album_id, key) == ("ALBUM1", "KEY1")
            if token == self.fail_page:
                return httpx.Response(500)
            a, b, nxt = self.pages[token]
            return httpx.Response(200, text=batch_text(a, b, nxt))
        return httpx.Response(404)


@pytest.fixture()
def setup(tmp_path):
    google = FakeGoogle()
    album = Album(Database(tmp_path / "db.sqlite"), tmp_path, transport=httpx.MockTransport(google), pause=0)
    return album, google, tmp_path


def test_clean_link():
    assert clean_link("Check out my album https://photos.app.goo.gl/AbC123xyz ") == LINK
    assert clean_link(SHARE) == SHARE
    for bad in ["https://example.com/x", "photos.app.goo.gl/abc", "https://photos.google.com/album/x", ""]:
        with pytest.raises(AlbumError):
            clean_link(bad)


def test_parse_page_and_batch():
    urls, token = parse_album_page(page_html(0, 3, "T1"))
    assert urls == [url(0), url(1), url(2)] and token == "T1"
    urls, token = parse_batch(batch_text(3, 5, None))
    assert urls == [url(3), url(4)] and token is None
    # Unknown page layout: still finds the album photos on the page (not the owner's picture)
    urls, token = parse_album_page(f'<div data-x="{url(9)}=w200"></div><img src="https://lh3.googleusercontent.com/a/ME">')
    assert urls == [url(9)] and token is None
    with pytest.raises(AlbumError):
        parse_batch(")]}'\n\n[[\"er\",null]]")


def test_reads_whole_album_and_keeps_only_links(setup):
    album, google, tmp = setup
    album.set_link(LINK)
    asyncio.run(album.refresh())
    assert album.items == [url(n) for n in range(7)]
    assert album.error is None and album.fetched_at
    saved = json.loads((tmp / "album.json").read_text())
    assert saved["items"] == album.items and saved["link"] == LINK
    # nothing downloaded: only the list file
    assert sorted(p.name for p in tmp.iterdir()) == ["album.json", "db.sqlite"]
    # survives a restart
    again = Album(album.db, tmp)
    assert again.items == album.items and not again.due()


def test_failed_check_keeps_last_good_list(setup):
    album, google, _ = setup
    album.set_link(LINK)
    asyncio.run(album.refresh())
    google.down = True
    album.checked_at = 0
    asyncio.run(album.refresh())
    assert len(album.items) == 7
    assert "503" in album.error
    # a partial read (a later page fails) doesn't replace a fuller list either
    google.down = False
    google.fail_page = "T2"
    album.checked_at = 0
    asyncio.run(album.refresh())
    assert len(album.items) == 7 and "Read 5 photos" in album.error


def test_partial_read_used_when_nothing_better(setup):
    album, google, _ = setup
    google.fail_page = "T1"
    album.set_link(LINK)
    asyncio.run(album.refresh())
    assert album.items == [url(0), url(1), url(2)]
    assert album.error.startswith("Read 3 photos")


def test_daily_check_and_manual_limit(setup):
    album, google, _ = setup
    assert not album.due()  # no link yet
    album.set_link(LINK)
    assert album.due()
    asyncio.run(album.refresh())
    assert not album.due()
    album.checked_at -= 23 * 3600
    assert not album.due()
    album.checked_at -= 2 * 3600
    assert album.due()
    calls = google.calls
    album.checked_at = __import__("time").time()
    asyncio.run(album.refresh(manual=True))  # too soon after the last check
    assert google.calls == calls


def test_draw_covers_everything_before_repeating(setup):
    album, _, _ = setup
    album.items = [url(n) for n in range(5)]
    uploads = ["up-a.jpg", "up-b.jpg"]
    seen = album.draw(4, uploads) + album.draw(3, uploads)
    assert sorted(seen) == sorted(album.items + uploads)
    assert len(album.draw(30, uploads)) == 7


def test_changing_link_clears_list(setup):
    album, _, tmp = setup
    album.set_link(LINK)
    asyncio.run(album.refresh())
    album.set_link("")
    assert album.items == [] and not (tmp / "album.json").exists()
    assert album.status()["link"] == ""


def test_api(tmp_path, monkeypatch):
    import importlib

    from fastapi.testclient import TestClient

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "nostatic"))
    import app.main

    importlib.reload(app.main)
    with TestClient(app.main.app) as c:
        assert c.get("/api/album").json()["count"] == 0
        assert c.put("/api/album", json={"link": "https://example.com/nope"}).status_code == 400
        assert c.get("/api/photos/next").json() == []
        s = app.main.app.state.s
        s.album._transport = httpx.MockTransport(FakeGoogle())
        s.album._pause = 0
        r = c.put("/api/album", json={"link": LINK})
        assert r.status_code == 200 and r.json()["link"] == LINK
        for _ in range(50):
            if c.get("/api/album").json()["count"] == 7:
                break
            __import__("time").sleep(0.02)
        assert c.get("/api/album").json()["count"] == 7
        got = c.get("/api/photos/next?count=5").json()
        assert len(got) == 5 and all(u.startswith("https://lh3.googleusercontent.com/pw/") for u in got)
        assert c.get("/api/photos/next?local=1").json() == []
        assert c.put("/api/album", json={"link": ""}).json()["count"] == 0
