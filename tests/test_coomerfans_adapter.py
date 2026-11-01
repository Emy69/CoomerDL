"""
Coomerfans profile scraping (issue #124).

The site answers 503 under load. Resolution had no retries, so one 503 lost
the post being read and a 503 on a profile page stopped the scan for the rest
of the profile without saying so.
"""
import pytest
import requests

from conftest import FakeResponse, FakeSession
from downloader.adapters.coomerfans_adapter import CoomerfansAdapter
from downloader.adapters.http_retry import ScrapeCancelled

PROFILE_URL = "https://coomerfans.com/u/onlyfans/273860/someone"
POST_PATHS = [f"/p/386274{n:02d}/273860/onlyfans" for n in (10, 21, 29)]
POST_URLS = [f"https://coomerfans.com{path}" for path in POST_PATHS]


def coomerfans_handler(method, url, **kwargs):
    if "/p/" in url:
        post_id = url.rsplit("/p/")[1].split("/")[0]
        return FakeResponse(200, f'<img src="https://img1.coomerfans.com/{post_id}.jpg">')
    if "page=" in url:
        return FakeResponse(200, "")  # past the last page
    return FakeResponse(200, "".join(f'<a href="{p}">post</a>' for p in POST_PATHS))


class NullCache:
    """The adapter caches resolved posts in sqlite; tests resolve every time."""

    def load(self, *args):
        return None

    def store(self, *args):
        pass


@pytest.fixture
def make_adapter():
    logs = []

    def build(fail_plan=None, **kwargs):
        kwargs.setdefault("retry_interval", 0)
        session = FakeSession(coomerfans_handler, fail_plan=fail_plan)
        adapter = CoomerfansAdapter(
            session,
            log_callback=lambda site, msg: logs.append(msg),
            request_interval=0,
            **kwargs,
        )
        adapter._post_cache = NullCache()
        adapter._sleep = lambda seconds: None
        adapter.logs = logs
        adapter.session_double = session
        return adapter

    return build


def test_a_transient_503_no_longer_drops_the_post(make_adapter):
    adapter = make_adapter(fail_plan={POST_URLS[0]: 2})

    resolved = adapter._resolve_profile(PROFILE_URL)

    assert len(resolved["media"]) == 3
    assert adapter._failed_posts == []


def test_a_post_past_its_retries_is_recovered_by_the_final_sweep(make_adapter):
    """Four 503s exhaust the per-request budget; the end-of-profile pass saves it."""
    adapter = make_adapter(fail_plan={POST_URLS[1]: 4}, max_retries=3)

    resolved = adapter._resolve_profile(PROFILE_URL)

    assert len(resolved["media"]) == 3
    assert any("COOMERFANS_RETRYING_FAILED_POSTS" in m for m in adapter.logs)


def test_a_permanently_failing_post_is_reported_not_silently_skipped(make_adapter):
    adapter = make_adapter(fail_plan={POST_URLS[2]: 99}, max_retries=2)

    resolved = adapter._resolve_profile(PROFILE_URL)

    assert len(resolved["media"]) == 2  # the other two still come back
    assert any("COOMERFANS_FAILED_POSTS_SUMMARY" in m for m in adapter.logs)


def test_a_404_is_not_retried(make_adapter):
    adapter = make_adapter(max_retries=5)
    adapter.session_double.handler = lambda method, url, **kw: FakeResponse(404)

    with pytest.raises(requests.HTTPError):
        adapter._request("https://coomerfans.com/p/1/2/3")

    assert len(adapter.session_double.calls) == 1


def test_retry_after_is_honoured(make_adapter):
    adapter = make_adapter()
    response = FakeResponse(503, headers={"Retry-After": "7"})

    assert adapter._retry_delay(0, response) == 7.0


def test_backoff_grows_with_each_attempt(make_adapter):
    adapter = make_adapter(retry_interval=2.0)

    assert adapter._retry_delay(0) < adapter._retry_delay(3)


def test_cancelling_unwinds_instead_of_looping(make_adapter):
    adapter = make_adapter()
    adapter.should_cancel = lambda: True

    with pytest.raises(ScrapeCancelled):
        adapter._request("https://coomerfans.com/p/1/2/3")
