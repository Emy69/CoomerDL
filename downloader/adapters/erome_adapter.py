import os
import re
import uuid
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


class EromeAdapter:
    site_name = "erome"

    def __init__(self, session, headers=None, log_callback=None, tr=None):
        self.session = session
        self.headers = {k: str(v).encode("ascii", "ignore").decode("ascii")
                        for k, v in (headers or {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        }).items()}
        self.log_callback = log_callback
        self.tr = tr if tr else (lambda x, **kwargs: x.format(**kwargs))

    def log(self, message, **kwargs):
        if kwargs:
            message = self.tr(message, **kwargs)
        else:
            message = self.tr(message)
        if self.log_callback:
            self.log_callback(message)

    @staticmethod
    def clean_filename(filename):
        return re.sub(r'[<>:"/\\|?*]', "_", str(filename).split("?")[0])

    def can_handle(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return "erome" in host

    def _request_soup(self, url):
        response = self.session.get(url, headers=self.headers, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def resolve_url(self, url, download_images=True, download_videos=True, direct_download=False):
        soup = self._request_soup(url)

        if soup.find("h1", class_="username") or "/a/" not in url:
            return self._resolve_profile(url, soup, download_images, download_videos, direct_download)

        return self._resolve_album(url, soup, download_images, download_videos, direct_download)

    def _resolve_profile(self, profile_url, soup=None, download_images=True, download_videos=True, direct_download=False):
        soup = soup or self._request_soup(profile_url)

        username_tag = soup.find("h1", class_="username")
        username = username_tag.text.strip() if username_tag else "Unknown Profile"
        base_folder_name = self.clean_filename(username)

        media = []
        album_links = soup.find_all("a", class_="album-link")

        for album_link in album_links:
            href = album_link.get("href")
            if not href:
                continue

            album_url = urljoin(profile_url, href)
            try:
                album_data = self._resolve_album(
                    album_url,
                    soup=None,
                    download_images=download_images,
                    download_videos=download_videos,
                    direct_download=direct_download,
                    inherited_base_folder=base_folder_name,
                )
                media.extend(album_data["media"])
            except Exception as e:
                self.log("Error resolving album {url}: {error}", url=album_url, error=e)

        return {
            "mode": "profile",
            "folder_name": base_folder_name,
            "media": media,
        }

    def _resolve_album(
        self,
        album_url,
        soup=None,
        download_images=True,
        download_videos=True,
        direct_download=False,
        inherited_base_folder=None,
    ):
        soup = soup or self._request_soup(album_url)

        album_title = soup.find("h1").text if soup.find("h1") else "Unknown Album"
        album_folder_name = self.clean_filename(album_title)

        if direct_download and inherited_base_folder:
            effective_folder = inherited_base_folder
        elif inherited_base_folder:
            effective_folder = os.path.join(inherited_base_folder, album_folder_name)
        else:
            effective_folder = album_folder_name

        media = []
        seen_urls = set()

        if download_videos:
            for video in soup.find_all("video"):
                source = video.find("source")
                if not source:
                    continue
                src = source.get("src")
                if not src:
                    continue

                abs_video_src = urljoin(album_url, src)
                if abs_video_src in seen_urls:
                    continue
                seen_urls.add(abs_video_src)

                media.append({
                    "media_url": abs_video_src,
                    "post_id": None,
                    "title": album_folder_name,
                    "published": "",
                    "folder_name": effective_folder,
                    "resource_type": "Video",
                    "filename": self.clean_filename(os.path.basename(abs_video_src.split("?")[0])),
                })

        if download_images:
            for div in soup.select("div.img"):
                img = (
                    div.find("img", attrs={"data-src": True})
                    or div.find("img", attrs={"src": True})
                )
                if not img:
                    continue

                raw_src = img.get("data-src") or img.get("src")
                if not raw_src:
                    continue

                abs_img_src = urljoin(album_url, raw_src)
                lower_src = abs_img_src.lower()

                if lower_src.startswith("data:"):
                    continue
                if any(x in lower_src for x in ["/avatar/", "/users/", "/profile/", "/static/", "/assets/", "/images/"]):
                    continue
                if any(x in lower_src for x in ["bg.jpg", "background", "avatar", "cover", "logo", "icon", "banner", "profile"]):
                    continue
                if abs_img_src in seen_urls:
                    continue

                seen_urls.add(abs_img_src)

                filename = os.path.basename(abs_img_src.split("?")[0])
                if not filename:
                    filename = f"image_{uuid.uuid4().hex[:8]}.jpg"

                media.append({
                    "media_url": abs_img_src,
                    "post_id": None,
                    "title": album_folder_name,
                    "published": "",
                    "folder_name": effective_folder,
                    "resource_type": "Image",
                    "filename": self.clean_filename(filename),
                })

        return {
            "mode": "album",
            "folder_name": effective_folder,
            "media": media,
        }