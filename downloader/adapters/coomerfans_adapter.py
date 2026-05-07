import os
import re
from urllib.parse import urljoin, urlparse, parse_qs

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

    def can_handle(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return "coomerfans" in host

    def _request_soup(self, url):
        response = self.session.get(url, headers=self.headers, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def resolve_url(self, url, download_images=True, download_videos=True, direct_download=False):
        """
        Resolves a coomerfans URL and returns media data.
        Handles both user profiles and individual posts.
        """
        path = urlparse(url).path
        
        # Check if it's a user profile URL (e.g., /u/fansly/347884/petitesaki)
        if path.startswith("/u/"):
            return self._resolve_profile(url, download_images, download_videos, direct_download)
        # Check if it's a post URL (e.g., /p/77803830/347884/fansly)
        elif path.startswith("/p/"):
            return self._resolve_post(url, download_images, download_videos, direct_download)
        else:
            self.log("COOMERFANS_UNKNOWN_URL_TYPE", url=url)
            return {
                "folder_name": "coomerfans_unknown",
                "media": [],
            }

    def _resolve_profile(self, profile_url, download_images=True, download_videos=True, direct_download=False):
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
            
            while page <= max_pages:
                try:
                    if page == 1:
                        page_url = profile_url.split("?")[0]  # Remove existing query params
                    else:
                        page_url = profile_url.split("?")[0] + f"?page={page}"
                    
                    soup = self._request_soup(page_url)
                    page_media = self._extract_profile_posts(soup, service, user_id, username)
                    
                    if not page_media:
                        # No more posts found
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

    def _extract_profile_posts(self, soup, service, user_id, username):
        """
        Extracts post links from a profile page.
        Looks for post containers and extracts media from each post.
        """
        media = []
        
        # Common post container selectors - adjust based on actual HTML structure
        post_containers = soup.find_all("div", class_=re.compile("post|card|item", re.I))
        
        # If no results, try alternative selectors
        if not post_containers:
            post_containers = soup.find_all("a", href=re.compile(r"/p/\d+"))
        
        for container in post_containers:
            try:
                # Try to extract post link
                post_link = None
                if container.name == "a":
                    post_link = container.get("href")
                else:
                    link = container.find("a", href=re.compile(r"/p/\d+"))
                    if link:
                        post_link = link.get("href")
                
                if post_link and not post_link.startswith("http"):
                    post_link = urljoin("https://coomerfans.com", post_link)
                
                if post_link:
                    post_media = self._resolve_post(post_link)
                    media.extend(post_media.get("media", []))
            
            except Exception as e:
                self.log("COOMERFANS_ERROR_EXTRACTING_POST", error=e)
                continue
        
        return media

    def _resolve_post(self, post_url, download_images=True, download_videos=True, direct_download=False):
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
            
            self.log("COOMERFANS_PROCESSING_POST", url=post_url, post_id=post_id)
            
            soup = self._request_soup(post_url)
            media = []
            
            # Extract images
            if download_images:
                # Look for images in common containers
                images = soup.find_all("img", src=re.compile(r"img\d+\.coomerfans\.com", re.I))
                
                for img in images:
                    src = img.get("src")
                    if src and not any(x in src.lower() for x in ["avatar", "profile", "logo", "icon"]):
                        if not src.startswith("http"):
                            src = urljoin(post_url, src)
                        
                        if src:
                            filename = self.clean_filename(os.path.basename(src.split("?")[0]))
                            if not filename or filename == ".":
                                filename = f"image_{post_id}.jpg"
                            
                            media.append({
                                "media_url": src,
                                "post_id": post_id,
                                "title": folder_name,
                                "published": "",
                                "folder_name": folder_name,
                                "resource_type": "Image",
                                "filename": filename,
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
                        
                        filename = self.clean_filename(os.path.basename(video_src.split("?")[0]))
                        if not filename or filename == ".":
                            filename = f"video_{post_id}.mp4"
                        
                        media.append({
                            "media_url": video_src,
                            "post_id": post_id,
                            "title": folder_name,
                            "published": "",
                            "folder_name": folder_name,
                            "resource_type": "Video",
                            "filename": filename,
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

    def _extract_direct_media(self, soup, post_url, post_id):
        """
        Extracts media URLs directly from page elements.
        Supports various HTML structures for media containers.
        """
        media = []
        
        # Look for image links that point to the img1.coomerfans.com domain
        img_links = soup.find_all("a", href=re.compile(r"img\d+\.coomerfans\.com", re.I))
        
        for link in img_links:
            href = link.get("href")
            if href and not href.startswith("http"):
                href = urljoin(post_url, href)
            
            if href and "coomerfans.com" in href.lower():
                filename = self.clean_filename(os.path.basename(href.split("?")[0]))
                if not filename:
                    filename = f"media_{post_id}.jpg"
                
                media.append({
                    "media_url": href,
                    "filename": filename,
                })
        
        return media
