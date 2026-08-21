import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


class CoomerfansAdapter:
    site_name = "coomerfans"

    def __init__(self, session, headers=None, log_callback=None, tr=None):
        self.session = session
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://coomerfans.com/",
        }
        self.log_callback = log_callback
        self.tr = tr if tr else (lambda x, **kwargs: x.format(**kwargs) if kwargs else x)

    def log(self, message, **kwargs):
        if kwargs:
            message = self.tr(message, **kwargs)
        else:
            message = self.tr(message)
        if self.log_callback:
            self.log_callback(self.site_name, message)

    @staticmethod
    def clean_filename(filename):
        return re.sub(r'[<>:"/\\|?*]', "_", str(filename).split("?")[0])

    def _request_soup(self, url):
        response = self.session.get(url, headers=self.headers, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _resolve_profile(self, profile_url, download_images=True, download_videos=True):
        """
        Resolves a user profile page and collects all posts.
        URL format: /u/{service}/{user_id}/{username}?page={page}
        """
        try:
            path_parts = urlparse(profile_url).path.strip("/").split("/")
            if len(path_parts) >= 4:
                service = path_parts[1]  # e.g., 'fansly'
                user_id = path_parts[2]  # e.g., '347884'
                username = path_parts[3]  # e.g., 'petitesaki'
            else:
                service = "unknown"
                user_id = "unknown"
                username = "profile"

            base_folder_name = self.clean_filename(f"{service}_{username}_{user_id}")

            self.log("COOMERFANS_PROCESSING_PROFILE", url=profile_url, username=username)

            media = []
            page = 1
            max_pages = 100  # Safety limit to prevent infinite loops
            seen_post_links = set()

            while page <= max_pages:
                try:
                    if page == 1:
                        page_url = profile_url.split("?")[0]  # Remove existing query params
                    else:
                        page_url = profile_url.split("?")[0] + f"?page={page}"

                    soup = self._request_soup(page_url)
                    posts_before = len(seen_post_links)
                    page_media = self._extract_profile_posts(
                        soup,
                        service,
                        user_id,
                        username,
                        download_images,
                        download_videos,
                        seen_post_links,
                    )

                    if len(seen_post_links) == posts_before:
                        # No new posts: end reached, or the site clamps
                        # out-of-range pages to the last one
                        break

                    media.extend(page_media)
                    page += 1

                except Exception as e:
                    self.log("COOMERFANS_ERROR_PROCESSING_PAGE", page=page, error=e)
                    break

            return {
                "mode": "profile",
                "folder_name": base_folder_name,
                "media": media,
            }

        except Exception as e:
            self.log("COOMERFANS_ERROR_RESOLVING_PROFILE", url=profile_url, error=e)
            return {
                "folder_name": "coomerfans_profile",
                "media": [],
            }

    def _extract_profile_posts(self, soup, service, user_id, username, download_images=True, download_videos=True, seen_links=None):
        """
        Extracts post links from a profile page.
        Looks for post containers and extracts media from each post.
        """
        media = []
        profile_folder = self.clean_filename(f"{service}_{username}_{user_id}")

        if seen_links is None:
            seen_links = set()
        for link in soup.find_all("a", href=re.compile(r"^/p/\d+")):
            href = link.get("href")
            if not href or href in seen_links:
                continue
            seen_links.add(href)

            try:
                post_link = urljoin("https://coomerfans.com", href)
                post_media = self._resolve_post(
                    post_link,
                    download_images=download_images,
                    download_videos=download_videos,
                    profile_user_id=profile_folder,
                )
                media.extend(post_media.get("media", []))
            except Exception as e:
                self.log("COOMERFANS_ERROR_EXTRACTING_POST", error=e)
                continue

        return media

    def _resolve_post(self, post_url, download_images=True, download_videos=True, profile_user_id=None):
        """
        Resolves a single post and extracts media.
        URL format: /p/{post_id}/{user_id}/{service}
        """
        try:
            path_parts = urlparse(post_url).path.strip("/").split("/")
            if len(path_parts) >= 4:
                post_id = path_parts[1]  # e.g., '77803830'
                user_id = path_parts[2]  # e.g., '347884'
                service = path_parts[3]  # e.g., 'fansly'
            else:
                post_id = "unknown"
                user_id = "unknown"
                service = "unknown"

            folder_name = self.clean_filename(f"{service}_post_{post_id}")
            entry_user_id = profile_user_id or self.clean_filename(f"{service}_{user_id}")

            self.log("COOMERFANS_PROCESSING_POST", url=post_url, post_id=post_id)

            soup = self._request_soup(post_url)
            media = []
            seen_urls = set()

            # Extract images
            if download_images:
                # Look for images in common containers
                images = soup.find_all("img", src=re.compile(r"img\d+\.coomerfans\.com", re.I))

                for img in images:
                    src = img.get("src")
                    if src and not any(x in src.lower() for x in ["avatar", "profile", "logo", "icon"]):
                        if not src.startswith("http"):
                            src = urljoin(post_url, src)

                        if src and src not in seen_urls:
                            seen_urls.add(src)
                            media.append({
                                "media_url": src,
                                "post_id": post_id,
                                "title": folder_name,
                                "published": "",
                                "user_id": entry_user_id,
                                "resource_type": "Image",
                            })

            # Extract videos
            if download_videos:
                videos = soup.find_all("video")

                for video in videos:
                    video_src = video.get("src")

                    if not video_src:
                        source = video.find("source")
                        if source:
                            video_src = source.get("src")

                    if video_src:
                        if not video_src.startswith("http"):
                            video_src = urljoin(post_url, video_src)

                        if video_src in seen_urls:
                            continue
                        seen_urls.add(video_src)
                        media.append({
                            "media_url": video_src,
                            "post_id": post_id,
                            "title": folder_name,
                            "published": "",
                            "user_id": entry_user_id,
                            "resource_type": "Video",
                        })

            return {
                "mode": "post",
                "folder_name": folder_name,
                "media": media,
            }

        except Exception as e:
            self.log("COOMERFANS_ERROR_RESOLVING_POST", url=post_url, error=e)
            return {
                "folder_name": "coomerfans_post",
                "media": [],
            }
