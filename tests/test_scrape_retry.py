"""
The retry behaviour every scraping adapter shares (RetryingScraper).

Erome and jpg5 had the same single-attempt weakness that broke coomerfans in
issue #124, so they are covered here through the mixin they all use.
"""
import pytest
import requests

from conftest import FakeResponse, FakeSession
from downloader.adapters.erome_adapter import EromeAdapter
from downloader.adapters.http_retry import RETRYABLE_STATUS_CODES, ScrapeCancelled
from downloader.adapters.jpg5_adapter import Jpg5Adapter

PAGE = "<html><body><h1 class='username'>someone</h1></body></html>"
URL = "https://example.com/gallery"


def serve(body=PAGE):
    return lambda method, url, **kwargs: FakeResponse(200, body)


@pytest.fixture(params=[EromeAdapter, Jpg5Adapter], ids=["erome", "jpg5"])
def adapter_class(request):
    return request.param


def build(adapter_class, session, **kwargs):
    kwargs.setdefault("max_retries", 3)
    kwargs.setdefault("retry_interval", 0)
    adapter = adapter_class(session, log_callback=lambda site, msg: None, **kwargs)
    adapter._sleep = lambda seconds: None
    return adapter


def test_recovers_from_a_burst_of_transient_errors(adapter_class):
    session = FakeSession(serve(), fail_plan={URL: 2})
    adapter = build(adapter_class, session)

    adapter._request_soup(URL)

    assert len(session.calls) == 3  # two failures, then the page


def test_gives_up_after_the_retry_budget_and_raises(adapter_class):
    """Silence here is what made a failure look like an empty page."""
    session = FakeSession(lambda method, url, **kw: FakeResponse(503))
    adapter = build(adapter_class, session)

    with pytest.raises(requests.HTTPError):
        adapter._request_soup(URL)

    assert len(session.calls) == 4  # the attempt plus three retries


def test_cancelling_unwinds_as_scrape_cancelled(adapter_class):
    adapter = build(adapter_class, FakeSession(serve()))
    adapter.should_cancel = lambda: True

    with pytest.raises(ScrapeCancelled):
        adapter._request_soup(URL)


@pytest.mark.parametrize("status", RETRYABLE_STATUS_CODES)
def test_transient_statuses_are_retried(adapter_class, status):
    session = FakeSession(serve(), fail_plan={URL: 1}, fail_status=status)
    adapter = build(adapter_class, session)

    adapter._request_soup(URL)

    assert len(session.calls) == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410])
def test_permanent_statuses_are_not_retried(adapter_class, status):
    session = FakeSession(lambda method, url, **kw: FakeResponse(status))
    adapter = build(adapter_class, session)

    with pytest.raises(requests.HTTPError):
        adapter._request_soup(URL)

    assert len(session.calls) == 1


def test_connection_errors_are_retried(adapter_class):
    attempts = {"n": 0}

    def flaky(method, url, **kwargs):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise requests.exceptions.ConnectionError("dropped")
        return FakeResponse(200, PAGE)

    adapter = build(adapter_class, FakeSession(flaky))

    adapter._request_soup(URL)

    assert attempts["n"] == 3


def test_jpg5_still_parses_bytes_so_the_meta_charset_is_honoured():
    """jpg5 pages declare their encoding in a meta tag, so bs4 gets raw bytes."""
    gallery = """<html><head><meta charset="utf-8"></head><body>
    <div class="list-item c8 gutter-margin-right-bottom">
      <a class="image-container --media" href="/img/one"></a>
    </div></body></html>"""
    adapter = build(Jpg5Adapter, FakeSession(serve(gallery)))

    soup = adapter._request_soup(URL, raw=True)

    assert soup.find("a", class_="image-container --media") is not None
