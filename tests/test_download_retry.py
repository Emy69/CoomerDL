"""
The download side of the retry policy (BaseApiDownloader.safe_request).

Downloading a bunkr album left three files failed while the log still said
"All downloads completed or cancelled". Two causes: 429 was retried with a
flat delay that burned four attempts in about six seconds, and 403/404
outside coomer/kemono failed with no log line at all.
"""
import time

import pytest

from conftest import FakeResponse, FakeSession
from downloader.core.base_api_downloader import BaseApiDownloader

URL = "https://c4s5-b.cdn.cr/storage/media/b3d7d03d-f92c-435f-bf31-a937532adfb6.mp4?n=x.mp4"
DOMAIN = "c4s5-b.cdn.cr"


@pytest.fixture
def make_downloader(isolated_cwd, tr):
    def build(status=200, headers=None, retry_interval=2.0, max_retries=3):
        session = FakeSession(lambda method, url, **kw: FakeResponse(status, headers=headers))
        downloader = BaseApiDownloader(
            download_folder="downloads",
            max_retries=max_retries,
            retry_interval=retry_interval,
            rate_limit_interval=0,
            tr=tr,
        )
        downloader.session = session
        downloader.logs = []
        downloader.log_callback = lambda domain, message: downloader.logs.append(message)
        downloader.session_double = session
        return downloader

    return build


def test_429_backs_off_instead_of_hammering(make_downloader, no_sleep):
    downloader = make_downloader(status=429)

    assert downloader.safe_request(URL) is None

    assert len(no_sleep) == 3  # the last attempt does not wait
    assert no_sleep[0] < no_sleep[1] < no_sleep[2]
    assert sum(no_sleep) > 12  # it used to be a flat 2 + 2 + 2


def test_retry_after_is_honoured(make_downloader, no_sleep):
    downloader = make_downloader(status=429, headers={"Retry-After": "12"})

    downloader.safe_request(URL)

    assert no_sleep == [12.0, 12.0, 12.0]


def test_an_absurd_retry_after_is_ignored(make_downloader, no_sleep):
    """A host asking for an hour should not freeze the download."""
    downloader = make_downloader(status=429, headers={"Retry-After": "3600"})

    downloader.safe_request(URL)

    assert all(delay < 60 for delay in no_sleep)


def test_a_burst_of_errors_trips_a_domain_cooldown(make_downloader, no_sleep):
    downloader = make_downloader(status=429)

    downloader.safe_request(URL)

    state = downloader.domain_error_state[DOMAIN]
    assert state["burst_count"] == 4
    assert state["cooldown_until"] > time.time()


def test_a_success_clears_the_domain_state(make_downloader):
    downloader = make_downloader(status=200)
    downloader.domain_error_state[DOMAIN]["burst_count"] = 3

    assert downloader.safe_request(URL) is not None
    assert downloader.domain_error_state[DOMAIN]["burst_count"] == 0


def test_403_is_reported_and_not_retried(make_downloader):
    """This used to burn four attempts and log nothing at all."""
    downloader = make_downloader(status=403)

    assert downloader.safe_request(URL) is None

    assert len(downloader.session_double.calls) == 1
    assert any("FINAL_FAILURE_ACCESSING_URL" in m for m in downloader.logs)


def test_every_exhausted_request_says_why_it_gave_up(make_downloader, no_sleep):
    downloader = make_downloader(status=503)

    downloader.safe_request(URL)

    assert downloader.logs[-1].startswith("FINAL_FAILURE_ACCESSING_URL")


def test_cancelling_during_a_cooldown_returns_immediately(make_downloader):
    downloader = make_downloader(status=429)
    downloader.domain_error_state[DOMAIN]["cooldown_until"] = time.time() + 999
    downloader.cancel_requested.set()

    started = time.time()
    assert downloader.safe_request(URL) is None
    assert time.time() - started < 1.0


def test_the_completion_message_reports_failures(make_downloader):
    downloader = make_downloader()
    downloader.failed_files = ["a", "b", "c"]

    downloader.shutdown_executor()

    assert downloader.logs[-1].startswith("DOWNLOAD_SUMMARY_FAILED")


def test_a_clean_run_reports_no_failures(make_downloader):
    downloader = make_downloader()

    downloader.shutdown_executor()

    assert not any("DOWNLOAD_SUMMARY_FAILED" in m for m in downloader.logs)
