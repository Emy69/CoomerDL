"""
Bunkr resolution (issue #125).

The site stopped putting the file URL in the download button, so every link
resolved back to the page itself and the HTML was saved as the file. The
fixtures below are the page source from that report.
"""
import json

import pytest

from conftest import FakeResponse, FakeSession
from downloader.adapters.bunkr_adapter import BunkrAdapter
from downloader.adapters.http_retry import ScrapeCancelled

FILE_URL = "https://bunkr.cr/f/2020-07-05_501576198"
ALBUM_URL = "https://bunkr.cr/a/xxxxxxxx"
API_URL = "https://get.bunkrr.su/api/_001_v2"

DOWNLOAD_PAGE = """<!DOCTYPE html>
<html lang="en" class="dark"><head>
<title>Download 2020-07-05_501576198.mp4</title>
<script>var ogname = "2020-07-05_501576198.mp4";</script>
</head><body>
<p class="mt-3 text-center">
  <a id="download-btn" class="btn btn-main btn-lg rounded-full px-6 font-semibold
     ic-download-01 ic-before before:text-lg" href="#" data-id="31751406">Download</a>
</p>
<script>
const SIGN_SERVICE_URL = 'https://glb-apisign.cdn.cr/sign';
fetch('/api/_001_v2', {method: 'POST'})
</script>
</body></html>"""

FILE_PAGE = """<html><body>
<div class="flex w-full md:w-auto gap-4">
  <a class="btn btn-main btn-lg rounded-full px-6 font-semibold flex-1
     ic-download-01 ic-before before:text-lg"
     href="https://get.bunkrr.su/file/31751406">Download</a>
</div></body></html>"""

# Deliberately not the classes the old code matched on: an album must still
# resolve after the site restyles its grid.
ALBUM_PAGE = """<html><body><h1 class="truncate">My Album</h1>
<div class="some-brand-new-class-name">
  <a class="whatever" href="/f/alpha-abc"><img src="/thumb1.jpg"></a>
  <a class="whatever" href="/f/beta-def"><img src="/thumb2.jpg"></a>
  <a class="whatever" href="/f/alpha-abc">duplicate link</a>
</div></body></html>"""


def bunkr_handler(sign_status=200):
    def handler(method, url, **kwargs):
        if url.endswith("/api/_001_v2"):
            assert json.loads(kwargs["data"]) == {"id": "31751406"}
            return FakeResponse(200, payload={
                "mediafiles": "https://mlk-bk.cdn.gigachad-cdn.ru",
                "path": "/2020-07-05_501576198.mp4",
                "original": "2020-07-05_501576198.mp4",
            })
        if "/sign" in url:
            if sign_status != 200:
                return FakeResponse(sign_status)
            assert kwargs["params"]["path"] == "/2020-07-05_501576198.mp4"
            return FakeResponse(200, payload={"token": "TOK123", "ex": "1757000000"})
        if "/file/" in url:
            return FakeResponse(200, DOWNLOAD_PAGE)
        if "/f/" in url:
            return FakeResponse(200, FILE_PAGE)
        if "/a/" in url:
            return FakeResponse(200, ALBUM_PAGE)
        raise AssertionError(f"unexpected url {url}")

    return handler


@pytest.fixture
def make_adapter():
    logs = []

    def build(session, **kwargs):
        kwargs.setdefault("retry_interval", 0)
        adapter = BunkrAdapter(session, log_callback=lambda site, msg: logs.append(msg), **kwargs)
        adapter._sleep = lambda seconds: None
        adapter.logs = logs
        return adapter

    return build


def test_file_url_resolves_to_the_signed_media_url(make_adapter):
    """The bug in #125: this used to hand back the page itself."""
    adapter = make_adapter(FakeSession(bunkr_handler()))

    resolved = adapter.resolve_url(FILE_URL)

    assert len(resolved["media"]) == 1
    url = resolved["media"][0]["media_url"]
    assert url.startswith("https://mlk-bk.cdn.gigachad-cdn.ru/2020-07-05_501576198.mp4?")
    assert "token=TOK123" in url
    assert "ex=1757000000" in url
    assert "n=2020-07-05_501576198.mp4" in url


def test_album_resolves_without_relying_on_layout_classes(make_adapter):
    adapter = make_adapter(FakeSession(bunkr_handler()))

    resolved = adapter.resolve_url(ALBUM_URL)

    # three anchors, one of them a duplicate
    assert len(resolved["media"]) == 2
    assert resolved["folder_name"].startswith("My Album_")
    assert all("token=TOK123" in m["media_url"] for m in resolved["media"])


def test_transient_5xx_on_the_api_is_retried(make_adapter):
    session = FakeSession(bunkr_handler(), fail_plan={API_URL: 2})
    adapter = make_adapter(session)

    resolved = adapter.resolve_url(FILE_URL)

    assert len(resolved["media"]) == 1
    assert sum("SCRAPE_RETRYING_REQUEST" in m for m in adapter.logs) == 2


def test_signing_failure_falls_back_to_the_unsigned_url(make_adapter):
    adapter = make_adapter(FakeSession(bunkr_handler(sign_status=500)), max_retries=1)

    resolved = adapter.resolve_url(FILE_URL)

    assert len(resolved["media"]) == 1
    assert "token=" not in resolved["media"][0]["media_url"]
    assert any("BUNKR_SIGNING_FAILED" in m for m in adapter.logs)


@pytest.mark.parametrize("candidate", ["#", "", None, "https://bunkr.cr/", "javascript:void(0)"])
def test_placeholder_hrefs_are_never_treated_as_files(candidate):
    """href="#" is what made the app save the HTML page as a .mp4."""
    assert BunkrAdapter._is_usable_media_url(candidate) is False


def test_a_real_url_is_accepted():
    assert BunkrAdapter._is_usable_media_url("https://bunkr.cr/f/x#") is True


def test_cancelling_mid_album_keeps_what_was_already_resolved(make_adapter):
    adapter = make_adapter(FakeSession(bunkr_handler()))
    calls = {"n": 0}

    def cancel_after_the_first_file():
        calls["n"] += 1
        return calls["n"] > 6

    adapter.should_cancel = cancel_after_the_first_file

    resolved = adapter.resolve_url(ALBUM_URL)

    assert len(resolved["media"]) == 1


def test_cancelling_before_the_first_request_unwinds(make_adapter):
    adapter = make_adapter(FakeSession(bunkr_handler()))
    adapter.should_cancel = lambda: True

    with pytest.raises(ScrapeCancelled):
        adapter.resolve_url(ALBUM_URL)


def test_both_downloader_entry_points_handle_cancellation():
    import inspect

    from downloader.bunkr import BunkrDownloader

    source = inspect.getsource(BunkrDownloader)
    assert source.count("except ScrapeCancelled:") == 2
