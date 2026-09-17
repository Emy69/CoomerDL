import random
import threading
import time

import requests
from bs4 import BeautifulSoup

# File hosts return 429/503 when they are under load. Without retries a
# temporary error looks like missing content, so every scraping request
# goes through RetryingScraper._request().
RETRYABLE_STATUS_CODES = (408, 425, 429, 500, 502, 503, 504)
MAX_RETRY_DELAY = 30.0
DEFAULT_TIMEOUT = 20


class ScrapeCancelled(Exception):
    """Raised to unwind scraping when the user cancels the download."""


class RetryingScraper:
    """
    Retry, backoff and throttling for adapters that scrape HTML pages.

    Adapters mix this in, call _init_retry() from __init__ and use
    _request()/_request_soup() instead of session.get().
    """

    def _init_retry(self, max_retries=3, retry_interval=2.0, request_interval=0.0,
                    should_cancel=None, timeout=DEFAULT_TIMEOUT):
        self.max_retries = max(0, int(max_retries))
        self.retry_interval = max(0.0, float(retry_interval))
        self.request_interval = max(0.0, float(request_interval))
        self.request_timeout = timeout
        self.should_cancel = should_cancel
        self._throttle_lock = threading.Lock()
        self._last_request_time = 0.0

    def _scrape_log(self, key, **kwargs):
        """Override in adapters whose log() does not translate its argument."""
        self.log(key, **kwargs)

    def _cancelled(self):
        return callable(getattr(self, "should_cancel", None)) and self.should_cancel()

    def _sleep(self, seconds):
        """Sleep in short slices so cancellation is picked up quickly."""
        deadline = time.monotonic() + max(0.0, seconds)
        while True:
            if self._cancelled():
                raise ScrapeCancelled()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.2, remaining))

    def _throttle(self):
        """Keep a minimum gap between scraping requests."""
        if self.request_interval <= 0:
            return
        with self._throttle_lock:
            wait = self.request_interval - (time.monotonic() - self._last_request_time)
            if wait > 0:
                time.sleep(min(wait, self.request_interval))
            self._last_request_time = time.monotonic()

    def _retry_delay(self, attempt, response=None):
        if response is not None:
            raw = response.headers.get("Retry-After")
            if raw:
                try:
                    retry_after = float(raw)
                except (TypeError, ValueError):
                    pass
                else:
                    if retry_after >= 0:
                        return min(retry_after, MAX_RETRY_DELAY)

        base = self.retry_interval if self.retry_interval > 0 else 1.0
        delay = min(base * (2 ** attempt), MAX_RETRY_DELAY)
        # Jitter so parallel workers do not retry at the same time.
        return delay + random.uniform(0, min(1.0, delay * 0.25))

    @staticmethod
    def _is_retryable(error, response):
        if response is None:
            return isinstance(error, (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ))
        return response.status_code in RETRYABLE_STATUS_CODES

    def _request(self, url, method="GET", **kwargs):
        kwargs.setdefault("headers", self.headers)
        kwargs.setdefault("timeout", self.request_timeout)

        attempts = self.max_retries + 1
        last_error = None

        for attempt in range(attempts):
            if self._cancelled():
                raise ScrapeCancelled()

            self._throttle()

            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_error = e
                response = getattr(e, "response", None)

                if not self._is_retryable(e, response) or attempt == attempts - 1:
                    raise

                delay = self._retry_delay(attempt, response)
                self._scrape_log(
                    "SCRAPE_RETRYING_REQUEST",
                    url=url,
                    reason=response.status_code if response is not None else type(e).__name__,
                    delay=round(delay, 1),
                    attempt=attempt + 1,
                    total=attempts,
                )
                self._sleep(delay)

        raise last_error

    def _request_soup(self, url, raw=False, **kwargs):
        response = self._request(url, **kwargs)
        return BeautifulSoup(response.content if raw else response.text, "html.parser")
