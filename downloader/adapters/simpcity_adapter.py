import base64
import json
import os
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from downloader.adapters.http_retry import RetryingScraper

# The TLD is left open: these hosts move (jpg5.su became goonbox.cr).
GOONBOX_IMAGE_RE = re.compile(r"^https?://(?:www\.)?goonbox\.[a-z]{2,}/img/([A-Za-z0-9_-]+)", re.I)
GOONBOX_ALBUM_RE = re.compile(r"^https?://(?:www\.)?goonbox\.[a-z]{2,}/(?:album|a)/([A-Za-z0-9_-]+)", re.I)
TURBO_EMBED_RE = re.compile(r"^https?://(?:www\.)?turbo\.[a-z]{2,}/embed/([A-Za-z0-9_-]+)", re.I)
TURBO_VIDEO_ID_RE = re.compile(r"""const\s+vvid\s*=\s*["']([A-Za-z0-9_-]+)["']""")


def unwrap_redirect(href):
    """XenForo hides some outbound links behind /redirect/?to=<base64>."""
    parsed = urlparse(href or "")
    if not parsed.path.rstrip("/").endswith("/redirect"):
        return href
    target = (parse_qs(parsed.query).get("to") or [""])[0]
    try:
        return base64.urlsafe_b64decode(target + "=" * (-len(target) % 4)).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return href


def is_goonbox_url(url):
    return bool(GOONBOX_IMAGE_RE.match(url or "") or GOONBOX_ALBUM_RE.match(url or ""))


class SimpCityAdapter(RetryingScraper):
    site_name = "simpcity"

    def __init__(self, cookies_path="resources/config/cookies/simpcity.json", log_callback=None, tr=None, session=None,
                 should_cancel=None, max_retries=3, retry_interval=2.0):
        self.cookies_path = cookies_path
        self.log_callback = log_callback
        self.tr = tr if tr else (lambda x, **kwargs: x.format(**kwargs) if kwargs else x)

        if session is None:
            try:
                import cloudscraper
            except ImportError as e:
                raise ImportError(
                    "SimpCity requires the 'cloudscraper' package. "
                    "Install it with: pip install cloudscraper"
                ) from e

            session = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )
        self.session = self.scraper = session
        self.headers = {}
        self._init_retry(max_retries=max_retries, retry_interval=retry_interval,
                         should_cancel=should_cancel)

        self.title_selector = "h1[class=p-title-value]"
        self.posts_selector = "div[class*=message-main]"
        self.post_content_selector = "div[class*=message-userContent]"
        self.images_selector = "img[class*=bbImage]"
        self.videos_selector = "video source"
        self.attachments_block_selector = "section[class=message-attachments]"
        self.attachments_selector = "a"
        self.next_page_selector = "a[class*=pageNav-jump--next]"

        self.set_cookies()

    def log(self, message, **kwargs):
        if kwargs:
            message = self.tr(message, **kwargs)
        else:
            message = self.tr(message)

        if self.log_callback:
            self.log_callback(self.site_name, message)

    def sanitize_folder_name(self, name):
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def set_cookies(self):
        if not os.path.exists(self.cookies_path):
            return

        with open(self.cookies_path, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        if isinstance(cookies, dict):
            if "name" in cookies and "value" in cookies:
                # single browser-export cookie object
                cookies = [cookies]
            else:
                # plain name -> value mapping, the format the settings
                # dialog placeholder suggests
                for name, value in cookies.items():
                    self.scraper.cookies.set(name, str(value))
                return

        for c in cookies:
            if isinstance(c, dict) and "name" in c and "value" in c:
                self.scraper.cookies.set(c["name"], c["value"])

    def fetch_page(self, url):
        response = self.scraper.get(url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    def resolve_thread(self, url, paginate=True, download_images=True, download_videos=True, download_attachments=True):
        self.log("SIMPCITY_PROCESSING_THREAD", url=url)

        all_media = []
        visited = set()
        current_url = url
        folder_name = None

        while current_url and current_url not in visited:
            visited.add(current_url)

            soup = self.fetch_page(current_url)

            if folder_name is None:
                title_element = soup.select_one(self.title_selector)
                folder_name = (
                    self.sanitize_folder_name(title_element.text.strip())
                    if title_element
                    else self.tr("SIMPCITY_DEFAULT_FOLDER")
                )

            page_media = self._extract_page_media(
                soup,
                base_url=current_url,
                folder_name=folder_name,
                download_images=download_images,
                download_videos=download_videos,
                download_attachments=download_attachments,
            )
            all_media.extend(page_media)

            if not paginate:
                break

            next_page = soup.select_one(self.next_page_selector)
            if next_page and next_page.get("href"):
                current_url = urljoin(current_url, next_page.get("href"))
            else:
                current_url = None

        return {
            "folder_name": folder_name or self.tr("SIMPCITY_DEFAULT_FOLDER"),
            "media": all_media,
        }

    def _entry(self, url, folder_name, filename, **extra):
        return {
            "media_url": url,
            "post_id": None,
            "title": folder_name,
            "published": "",
            "folder_name": folder_name,
            "filename": filename,
            **extra,
        }

    @staticmethod
    def _goonbox_link(tag):
        """The GoonBox page an image links to, if it is one of its thumbnails."""
        parent = tag.find_parent("a", href=True)
        if not parent:
            return None
        href = unwrap_redirect(parent["href"])
        return href if is_goonbox_url(href) else None

    def _extract_page_media(self, soup, base_url, folder_name, download_images=True, download_videos=True, download_attachments=True):
        media = []
        seen = set()

        message_inners = soup.select(self.posts_selector)
        for post in message_inners:
            post_content = post.select_one(self.post_content_selector)
            if not post_content:
                continue

            if download_images:
                for img in post_content.select(self.images_selector):
                    # A GoonBox embed shows a .md/.th thumbnail that the CDN
                    # refuses to serve on its own; the full image is resolved
                    # from the link around it, below.
                    if self._goonbox_link(img):
                        continue

                    src = img.get("src")
                    if not src:
                        continue
                    src = urljoin(base_url, src)
                    if src in seen:
                        continue
                    seen.add(src)

                    media.append(self._entry(src, folder_name, os.path.basename(urlparse(src).path) or "image"))

                for link in post_content.find_all("a", href=True):
                    href = unwrap_redirect(urljoin(base_url, link["href"]))
                    if not is_goonbox_url(href) or href in seen:
                        continue
                    seen.add(href)
                    media.append(self._entry(href, folder_name, None, embed="goonbox"))

            if download_videos:
                for video in post_content.select(self.videos_selector):
                    src = video.get("src")
                    if not src:
                        continue
                    src = urljoin(base_url, src)
                    if src in seen:
                        continue
                    seen.add(src)

                    media.append(self._entry(src, folder_name, os.path.basename(urlparse(src).path) or "video"))

                for frame in post_content.find_all("iframe"):
                    src = urljoin(base_url, frame.get("src") or frame.get("data-src") or "")
                    if not TURBO_EMBED_RE.match(src) or src in seen:
                        continue
                    seen.add(src)
                    media.append(self._entry(src, folder_name, None, embed="turbo", referer=base_url))

            if download_attachments:
                attachments_block = post_content.select_one(self.attachments_block_selector)
                if attachments_block:
                    for attachment in attachments_block.select(self.attachments_selector):
                        href = attachment.get("href")
                        if not href:
                            continue
                        href = urljoin(base_url, href)
                        if href in seen:
                            continue
                        seen.add(href)

                        media.append(self._entry(href, folder_name, os.path.basename(urlparse(href).path) or "attachment"))

        return media

    def resolve_embed(self, entry):
        """
        Turns a GoonBox or turbo.cr entry into the files behind it, each with
        the headers its host needs. Plain entries come back unchanged.
        """
        kind = entry.get("embed")
        if kind == "goonbox":
            return self._resolve_goonbox(entry)
        if kind == "turbo":
            return self._resolve_turbo(entry)
        return [entry]

    def _resolve_goonbox(self, entry):
        page = entry["media_url"]
        parsed = urlparse(page)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        # The CDN answers 403 unless the request says it comes from GoonBox.
        headers = {"Referer": origin + "/"}

        album = GOONBOX_ALBUM_RE.match(page)
        if album:
            images = self._goonbox_album_images(origin, album.group(1))
        else:
            code = GOONBOX_IMAGE_RE.match(page).group(1)
            data = self._request(f"{origin}/api/images/{code}", headers={"Accept": "application/json"}).json()
            images = [data.get("image") or {}]

        files = []
        for image in images:
            url = (image.get("original_url") or "").strip()
            if not url:
                continue
            name = image.get("original_filename") or os.path.basename(urlparse(url).path)
            files.append({**entry, "media_url": url, "filename": name, "headers": headers})
        return files

    def _goonbox_album_images(self, origin, code):
        images = []
        page, last = 1, 1
        while page <= last:
            data = self._request(f"{origin}/api/albums/{code}", params={"page": page},
                                 headers={"Accept": "application/json"}).json() or {}
            try:
                last = max(1, int((data.get("pagination") or {}).get("last_page") or 1))
            except (TypeError, ValueError):
                last = page
            batch = data.get("images") or []
            if not batch:
                break
            images.extend(batch)
            page += 1
        return images

    def _resolve_turbo(self, entry):
        embed = entry["media_url"]
        parsed = urlparse(embed)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        page = self._request(embed, headers={"Referer": entry.get("referer") or origin + "/"})
        match = TURBO_VIDEO_ID_RE.search(page.text)
        video_id = match.group(1) if match else TURBO_EMBED_RE.match(embed).group(1)

        data = self._request(f"{origin}/api/sign", params={"v": video_id},
                             headers={"Referer": embed, "Accept": "application/json"}).json() or {}
        url = data.get("url")
        if not url or str(data.get("success")).lower() != "true":
            return []

        # Turbo has only ever handed out direct files so far. A playlist would
        # need a segment downloader, so it is reported instead of saved as a
        # useless .m3u8.
        if urlparse(url).path.lower().endswith(".m3u8"):
            self.log("SIMPCITY_TURBO_STREAM_UNSUPPORTED", url=embed)
            return []

        extension = os.path.splitext(urlparse(url).path)[1] or ".mp4"
        name = data.get("original_filename") or f"{video_id}{extension}"
        # The link is signed and changes on every visit, so the embed is what
        # identifies the video in the database.
        return [{**entry, "media_url": url, "filename": name,
                 "headers": {"Referer": embed}, "record_url": embed}]
