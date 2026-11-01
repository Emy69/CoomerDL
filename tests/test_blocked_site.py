"""
Coomer and Kemono answer 403 from their DDoS protection while it is active.

The log used to show the raw HTTP error followed by "No posts found for this
user", which reads as if the profile were empty or the app were broken.
"""
import pytest

from conftest import FakeResponse, FakeSession
from downloader.downloader import Downloader

SITE = "coomer.st"


@pytest.fixture
def make_downloader(isolated_cwd, tr):
    def build(status, payload=None):
        downloader = Downloader(download_folder="downloads", tr=tr, rate_limit_interval=0)
        downloader.session = FakeSession(
            lambda method, url, **kw: FakeResponse(status, payload=payload))
        downloader.logs = []
        downloader.log_callback = lambda domain, message: downloader.logs.append(message)
        return downloader

    return build


def test_a_403_says_the_site_is_blocking(make_downloader):
    downloader = make_downloader(403)

    downloader.download_media(SITE, "someone", "onlyfans")

    assert "CK_SITE_BLOCKED" in downloader.logs
    assert "CK_NO_POSTS_FOUND_FOR_USER" not in downloader.logs
    assert "CK_ERROR_FETCHING_USER_POSTS" not in downloader.logs


def test_a_single_post_behind_a_403_is_not_reported_missing(make_downloader):
    downloader = make_downloader(403)

    downloader.download_single_post(SITE, "123", "onlyfans", "someone")

    assert "CK_SITE_BLOCKED" in downloader.logs
    assert "CK_NO_POST_FOUND_FOR_ID" not in downloader.logs


def test_an_empty_profile_is_still_reported_as_empty(make_downloader):
    downloader = make_downloader(200, payload=[])

    downloader.download_media(SITE, "someone", "onlyfans")

    assert "CK_NO_POSTS_FOUND_FOR_USER" in downloader.logs
    assert "CK_SITE_BLOCKED" not in downloader.logs
