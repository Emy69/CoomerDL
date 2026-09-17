import hashlib
import json
import re
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlparse, urlunparse

from downloader.adapters.http_retry import RetryingScraper, ScrapeCancelled

# The download button no longer carries the file URL in its href, only a
# data-id. The page JS exchanges that id for a signed URL through two
# endpoints. Both are read from the page so a domain change does not
# require a code change.
DEFAULT_API_ENDPOINT = "/api/_001_v2"
DEFAULT_SIGN_SERVICE = "https://glb-apisign.cdn.cr/sign"

API_ENDPOINT_RE = re.compile(r"""fetch\(\s*['"]([^'"]*/api/_[^'"]+)['"]""")
SIGN_SERVICE_RE = re.compile(r"""SIGN_SERVICE_URL\s*=\s*['"]([^'"]+)['"]""")
OG_NAME_RE = re.compile(r"""ogname\s*=\s*['"]([^'"]+)['"]""")
FILE_HREF_RE = re.compile(r"^(?:https?://[^/]+)?/f/")


class BunkrAdapter(RetryingScraper):
    site_name = "bunkr"

    def __init__(self, session, headers=None, log_callback=None, tr=None,
                 should_cancel=None, max_retries=3, retry_interval=2.0,
                 request_interval=0.0):
        self.session = session
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Referer": "https://bunkr.site/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.log_callback = log_callback
        self.tr = tr
        self._init_retry(
            max_retries=max_retries,
            retry_interval=retry_interval,
            request_interval=request_interval,
            should_cancel=should_cancel,
        )

    def translate(self, key, **kwargs):
        if callable(self.tr):
            try:
                return self.tr(key, **kwargs)
            except TypeError:
                text = self.tr(key)
                if kwargs:
                    try:
                        return text.format(**kwargs)
                    except Exception:
                        return text
                return text

        if kwargs:
            try:
                return key.format(**kwargs)
            except Exception:
                return key
        return key

    def log(self, message):
        if self.log_callback:
            self.log_callback(self.site_name, message)

    def _scrape_log(self, key, **kwargs):
        self.log(self.translate(key, **kwargs))

    def clean_filename(self, filename):
        return re.sub(r'[<>:"/\\|?*​]', "_", str(filename or "")).strip()

    def get_consistent_folder_name(self, url, default_name):
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        folder_name = f"{default_name}_{url_hash}"
        return self.clean_filename(folder_name)

    def resolve_url(self, url: str):
        if "/f/" in url:
            return self._resolve_f_url(url)

        return self._resolve_post_or_profile(url)

    @staticmethod
    def _is_usable_media_url(candidate):
        """Reject placeholders like href="#", which were being saved as files."""
        if not candidate:
            return False
        parsed = urlparse(candidate)
        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
            and bool(parsed.path.strip("/"))
        )

    @staticmethod
    def _with_query(url, **params):
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update({k: v for k, v in params.items() if v is not None})
        return urlunparse(parsed._replace(query=urlencode(query)))

    # ------------------------------------------------------------------
    # Direct-link resolution
    # ------------------------------------------------------------------

    def _sign_url(self, raw_url, page_html):
        """Exchange the raw media URL for the signed one."""
        match = SIGN_SERVICE_RE.search(page_html)
        sign_service = match.group(1) if match else DEFAULT_SIGN_SERVICE

        try:
            response = self._request(
                sign_service,
                params={"path": unquote(urlparse(raw_url).path)},
            )
            payload = response.json()
        except ScrapeCancelled:
            raise
        except Exception as e:
            # The unsigned URL still works on some mirrors, so try it anyway.
            self.log(self.translate("BUNKR_SIGNING_FAILED", url=raw_url, error=e))
            return raw_url

        token = payload.get("token")
        if not token:
            self.log(self.translate("BUNKR_SIGNING_FAILED", url=raw_url, error=payload))
            return raw_url

        return self._with_query(raw_url, token=token, ex=payload.get("ex"))

    def _resolve_via_api(self, page_url, page_html, file_id):
        match = API_ENDPOINT_RE.search(page_html)
        api_url = urljoin(page_url, match.group(1) if match else DEFAULT_API_ENDPOINT)

        headers = dict(self.headers)
        headers["Content-Type"] = "application/json"
        headers["Referer"] = page_url

        response = self._request(
            api_url,
            method="POST",
            data=json.dumps({"id": file_id}),
            headers=headers,
        )
        meta = response.json()

        raw_url = f"{meta.get('mediafiles') or ''}{meta.get('path') or ''}"
        if not self._is_usable_media_url(raw_url):
            return None

        original = meta.get("original")
        if not original:
            og_match = OG_NAME_RE.search(page_html)
            original = og_match.group(1) if og_match else None
        if original:
            raw_url = self._with_query(raw_url, n=original)

        return self._sign_url(raw_url, page_html)

    def _find_download_page(self, page_url, soup):
        """A /f/ page links to the page that holds the download button."""
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if href in ("", "#"):
                continue

            classes = " ".join(anchor.get("class") or [])
            if "/file/" in href or "download" in classes.lower() \
                    or "download" in anchor.get_text(strip=True).lower():
                return urljoin(page_url, href)

        return None

    def _extract_media_url(self, page_url, soup, depth=0):
        """
        Walk a /f/ page to the real file URL: data-id -> API -> signed URL,
        falling back to a direct href or an embedded media tag.
        """
        page_html = str(soup)
        button = soup.find(id="download-btn") or soup.find(attrs={"data-id": True})
        file_id = button.get("data-id") if button else None

        if file_id:
            try:
                media_url = self._resolve_via_api(page_url, page_html, file_id)
            except ScrapeCancelled:
                raise
            except Exception as e:
                self.log(self.translate("BUNKR_API_RESOLUTION_FAILED", url=page_url, error=e))
                media_url = None

            if media_url:
                return media_url

        if button is not None:
            candidate = urljoin(page_url, button.get("href") or "")
            if self._is_usable_media_url(candidate):
                return candidate

        video = soup.select_one("video#player[src], video#player source[src], video[src], video source[src]")
        if video is not None:
            candidate = urljoin(page_url, video.get("src") or "")
            if self._is_usable_media_url(candidate):
                return candidate

        if depth == 0:
            next_page = self._find_download_page(page_url, soup)
            if next_page and next_page != page_url:
                return self._extract_media_url(next_page, self._request_soup(next_page), depth=1)

        return None

    def _resolve_f_url(self, url, title="bunkr_post"):
        self.log(self.translate("BUNKR_RESOLVING_F_URL", url=url))

        folder_name = self.get_consistent_folder_name(url, "bunkr_post")
        media_url = self._extract_media_url(url, self._request_soup(url))

        if not media_url:
            self.log(self.translate("BUNKR_FINAL_DOWNLOAD_LINK_NOT_FOUND"))
            return {"folder_name": folder_name, "media": []}

        return {
            "folder_name": folder_name,
            "media": [
                {
                    "media_url": media_url,
                    "title": title,
                    "post_id": None,
                    "published": "",
                }
            ],
        }

    # ------------------------------------------------------------------
    # Album / profile pages
    # ------------------------------------------------------------------

    def _collect_file_links(self, page_url, soup):
        """
        Album pages are a grid of /f/ links. Match on the href instead of the
        layout classes, which change on every redesign.
        """
        links = []
        seen = set()

        for anchor in soup.find_all("a", href=FILE_HREF_RE):
            absolute = urljoin(page_url, anchor["href"])
            if absolute not in seen:
                seen.add(absolute)
                links.append(absolute)

        return links

    def _resolve_post_or_profile(self, url):
        soup = self._request_soup(url)

        title_tag = soup.find("h1", {"class": "truncate"}) or soup.find("h1")
        base_folder_name = self.clean_filename(title_tag.text.strip())[:50] if title_tag else ""
        folder_name = self.get_consistent_folder_name(url, base_folder_name or "bunkr_profile")

        media = []
        file_links = self._collect_file_links(url, soup)

        for file_url in file_links:
            if self._cancelled():
                break
            try:
                media.extend(self._resolve_f_url(file_url, title="bunkr_profile_item")["media"])
            except ScrapeCancelled:
                break
            except Exception as e:
                self.log(
                    self.translate(
                        "BUNKR_FAILED_RESOLVING_PROFILE_MEDIA_PAGE",
                        url=file_url,
                        error=e,
                    )
                )

        if not file_links:
            media.extend(self._resolve_embedded_media(url, soup))

        if not media:
            self.log(self.translate("BUNKR_NO_FILES_FOUND", url=url))

        return {
            "folder_name": folder_name,
            "media": media,
        }

    def _resolve_embedded_media(self, post_url, soup):
        """Fallback for pages that embed the media directly."""
        media = []
        seen = set()

        for tag in soup.select("figure img[src], video[src], video source[src]"):
            classes = " ".join(tag.get("class") or []).lower()
            if "blur" in classes or "opacity-20" in classes:
                continue  # blurred background image, not the file

            candidate = urljoin(post_url, tag.get("src") or "")
            if self._is_usable_media_url(candidate) and candidate not in seen:
                seen.add(candidate)
                media.append({
                    "media_url": candidate,
                    "title": "bunkr_post",
                    "post_id": None,
                    "published": "",
                })

        return media
