"""
SimpCity cookies used to sit in plain JSON next to the executable, readable by
anything that could open the folder. They are now encrypted for the Windows
user, and files saved by older versions keep working.
"""
import json

import pytest

from app.services.cookies_settings_service import CookiesSettingsService
from downloader.core import protected_json

COOKIES = [{"name": "xf_user", "value": "123,abcdef"}]

windows_only = pytest.mark.skipif(not protected_json.available(), reason="DPAPI is Windows only")


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "cookies" / "simpcity.json")


def test_round_trip(path):
    protected_json.save(path, COOKIES)

    assert protected_json.load(path) == COOKIES


def test_missing_file_is_none(path):
    assert protected_json.load(path) is None


@windows_only
def test_the_value_is_not_readable_on_disk(path):
    protected_json.save(path, COOKIES)

    with open(path, encoding="utf-8") as f:
        on_disk = f.read()
    assert "abcdef" not in on_disk
    assert protected_json.is_protected(json.loads(on_disk))


@windows_only
def test_a_tampered_file_raises_value_error(path):
    protected_json.save(path, COOKIES)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"dpapi": True, "data": "bm90IGVuY3J5cHRlZA=="}, f)

    with pytest.raises(ValueError):
        protected_json.load(path)


def test_plain_files_from_older_versions_still_load(path):
    service = CookiesSettingsService(path)
    service.ensure_parent_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(COOKIES, f)

    assert json.loads(service.load_cookies_text()) == COOKIES
    assert service.count_cookies() == 1


@windows_only
def test_plain_files_get_encrypted_once_read(path):
    service = CookiesSettingsService(path)
    service.ensure_parent_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(COOKIES, f)

    service.load_cookies_text()

    with open(path, encoding="utf-8") as f:
        assert "abcdef" not in f.read()
    assert protected_json.load(path) == COOKIES


def test_settings_service_save_and_clear(path):
    service = CookiesSettingsService(path)

    service.save_cookies_text(json.dumps(COOKIES))
    assert service.count_cookies() == 1

    service.clear_cookies()
    assert service.count_cookies() == 0
    assert service.load_cookies_text() == "{}"


def test_simpcity_reads_encrypted_cookies(path):
    from downloader.adapters.simpcity_adapter import SimpCityAdapter

    protected_json.save(path, COOKIES)
    adapter = SimpCityAdapter(cookies_path=path)

    assert adapter.scraper.cookies.get("xf_user") == "123,abcdef"
