"""
Naming downloaded files.

Bunkr serves every file under a UUID and puts the real name in the `n` query
parameter, so albums used to land as 51858954-a8c0-...mp4.
"""
import os

import pytest

from downloader.core.base_api_downloader import BaseApiDownloader

BUNKR_URL = (
    "https://c4s5-b.cdn.cr/storage/media/51858954-a8c0-42e9-941c-6d9e3b64f5e0.mp4"
    "?n=Street_Fighter_Chun-Li_4_v2_60.mp4&token=b7ec300d&ex=1789621602"
)


@pytest.fixture
def downloader(isolated_cwd, tr):
    instance = BaseApiDownloader(download_folder="downloads", tr=tr)
    instance.file_naming_mode = 0
    return instance


def test_the_real_name_is_taken_from_the_query(downloader):
    assert downloader._filename_from_url(BUNKR_URL) == "Street_Fighter_Chun-Li_4_v2_60.mp4"
    assert downloader.get_filename(BUNKR_URL) == "Street_Fighter_Chun-Li_4_v2_60_1.mp4"


@pytest.mark.parametrize("url,expected", [
    ("https://img1.coomerfans.com/abc/photo.jpg", "photo.jpg"),
    ("https://example.com/a/b/clip.mp4?token=x&ex=1", "clip.mp4"),
    ("https://example.com/a/b/clip.mp4", "clip.mp4"),
])
def test_urls_without_the_parameter_are_unchanged(downloader, url, expected):
    assert downloader._filename_from_url(url) == expected


@pytest.mark.parametrize("name,expected", [
    ("..%2F..%2F..%2Fevil.mp4", "evil.mp4"),
    ("C:%5CWindows%5Csystem32%5Cevil.mp4", "evil.mp4"),
    ("..", "uuid.mp4"),
    (".", "uuid.mp4"),
    ("", "uuid.mp4"),
])
def test_the_name_cannot_escape_the_download_folder(downloader, name, expected):
    """The value comes from the site, so only its basename is ever used."""
    assert downloader._filename_from_url(f"https://example.com/x/uuid.mp4?n={name}") == expected


def test_a_hostile_name_never_survives_into_the_path(downloader):
    filename = downloader.get_filename("https://example.com/x/uuid.mp4?n=..%2F..%2Fevil.mp4")

    assert "/" not in filename
    assert "\\" not in filename


def test_a_name_without_an_extension_borrows_the_one_from_the_path(downloader):
    assert downloader._filename_from_url("https://example.com/x/uuid.mp4?n=holiday") == "holiday.mp4"


@pytest.mark.parametrize("encoded,expected", [
    ("my+clip+2.mp4", "my clip 2.mp4"),
    ("my%20clip.mp4", "my clip.mp4"),
])
def test_encoded_spaces_are_decoded(downloader, encoded, expected):
    assert downloader._filename_from_url(f"https://example.com/x/u.mp4?n={encoded}") == expected


def test_the_media_folder_agrees_with_the_name(downloader):
    """The extension that picks videos/ must come from the same place as the name."""
    extension = os.path.splitext(downloader._filename_from_url(BUNKR_URL))[1].lower()

    folder = downloader.get_media_folder(extension, "album")

    assert folder.endswith(os.path.join("album", "videos"))


def test_naming_mode_1_still_keys_off_the_post_name(downloader):
    """Modes 1-3 build the name from the post, not from the URL."""
    downloader.file_naming_mode = 1

    filename = downloader.get_filename(BUNKR_URL, post_id="7", post_name="My Post")

    assert filename.startswith("My Post_1_")
    assert filename.endswith(".mp4")


def test_naming_mode_2_still_keys_off_the_post_name(downloader):
    downloader.file_naming_mode = 2

    filename = downloader.get_filename(BUNKR_URL, post_id="7", post_name="My Post")

    assert filename == "My Post - 7_1.mp4"
