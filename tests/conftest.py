"""Shared fixtures and HTTP doubles for the test suite.

Nothing here touches the network. The downloaders take a `session` (or build
one on `self.session`), so tests swap in `FakeSession` and describe the
responses the site would send.
"""
import json as _json
import os
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeResponse:
    """Enough of requests.Response for the downloaders and adapters."""

    def __init__(self, status_code=200, text="", payload=None, headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self._payload = payload

    @property
    def content(self):
        return self.text.encode("utf-8")

    def json(self):
        if self._payload is None:
            return _json.loads(self.text)
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error", response=self)


class FakeSession:
    """
    Routes requests through `handler(method, url, **kwargs)`.

    `fail_plan` maps a url to a number of failures to serve before the handler
    is consulted, which is how the transient 5xx cases are described.
    """

    def __init__(self, handler=None, fail_plan=None, fail_status=503):
        self.handler = handler or (lambda method, url, **kw: FakeResponse(200))
        self.fail_plan = dict(fail_plan or {})
        self.fail_status = fail_status
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))

        remaining = self.fail_plan.get(url, 0)
        if remaining:
            self.fail_plan[url] = remaining - 1
            return FakeResponse(self.fail_status)

        return self.handler(method, url, **kwargs)

    # BaseApiDownloader.safe_request calls session.get directly.
    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    @property
    def urls(self):
        return [url for _, url, _ in self.calls]


@pytest.fixture
def fake_session():
    return FakeSession


@pytest.fixture
def no_sleep(monkeypatch):
    """Collect the delays a retry loop asks for instead of waiting them out."""
    slept = []

    def record(seconds):
        slept.append(seconds)

    import downloader.adapters.http_retry as http_retry
    import downloader.core.base_api_downloader as base

    monkeypatch.setattr(base.time, "sleep", record)
    monkeypatch.setattr(http_retry.time, "sleep", record)
    return slept


@pytest.fixture
def isolated_cwd(tmp_path, monkeypatch):
    """
    BaseApiDownloader opens resources/config/downloads.db relative to the
    working directory, so tests run somewhere disposable to avoid writing
    into the real database.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs(tmp_path / "resources" / "config", exist_ok=True)
    return tmp_path


@pytest.fixture
def tr():
    """Translator stand-in: hand back the key so assertions can match on it."""
    return lambda key, **kwargs: key
