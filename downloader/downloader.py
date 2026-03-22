from concurrent.futures import as_completed

from downloader.core.base_api_downloader import BaseApiDownloader
from downloader.adapters.coomer_kemono_adapter import CoomerKemonoAdapter


class Downloader(BaseApiDownloader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_adapter = CoomerKemonoAdapter(
            session=self.session,
            headers=self.headers,
            log_callback=self.log_callback,
            tr=self.tr,
        )
        self.domain_name = "coomer"

    def fetch_user_posts(self, *args, **kwargs):
        kwargs.setdefault("cancel_event", self.cancel_requested)
        return self.api_adapter.fetch_user_posts(*args, **kwargs)

    def fetch_single_post(self, *args, **kwargs):
        return self.api_adapter.fetch_single_post(*args, **kwargs)

    def process_post(self, post, site):
        return self.api_adapter.extract_media_urls(post, site)

    def _collect_filtered_media(self, posts, site):
        collected = []

        for post in posts:
            current_post_id = post.get("id") or "unknown_id"
            title = post.get("title") or ""
            published_time = post.get("published") or ""

            media_urls = self.process_post(post, site)
            for media_url in media_urls:
                ext = media_url.rsplit(".", 1)[-1].lower() if "." in media_url else ""
                ext = f".{ext}" if ext else ""

                if (ext in self.image_extensions and not self.download_images) or \
                   (ext in self.video_extensions and not self.download_videos) or \
                   (ext in self.compressed_extensions and not self.download_compressed):
                    continue

                collected.append({
                    "media_url": media_url,
                    "post_id": current_post_id,
                    "title": title,
                    "published": published_time,
                })

        return collected

    def download_media(self, site, user_id, service, query=None, download_all=False, initial_offset=0, only_first_page=False):
        try:
            self.log("CK_STARTING_DOWNLOAD_PROCESS")

            posts = self.fetch_user_posts(
                site,
                user_id,
                service,
                query=query,
                initial_offset=initial_offset,
                log_fetching=download_all,
                only_first_page=only_first_page,
            )

            if not posts:
                self.log("CK_NO_POSTS_FOUND_FOR_USER")
                return

            if not download_all:
                posts = posts[:50]

            media_entries = self._collect_filtered_media(posts, site)
            self.total_files = len(media_entries)
            self.completed_files = 0

            futures = []

            for entry in media_entries:
                if self.download_mode == "queue":
                    self.process_media_element(
                        entry["media_url"],
                        user_id,
                        post_id=entry["post_id"],
                        post_name=entry["title"],
                        post_time=entry["published"],
                        download_id=entry["media_url"],
                    )
                else:
                    future = self.executor.submit(
                        self.process_media_element,
                        entry["media_url"],
                        user_id,
                        entry["post_id"],
                        entry["title"],
                        entry["published"],
                        entry["media_url"],
                    )
                    futures.append(future)

            self.futures = futures

            if self.download_mode == "multi":
                for future in as_completed(futures):
                    if self.cancel_requested.is_set():
                        break
                    future.result()

        except Exception as e:
            self.log("CK_ERROR_DURING_DOWNLOAD", error=e)
        finally:
            self.shutdown_executor()

    def download_single_post(self, site, post_id, service, user_id):
        try:
            posts = self.fetch_user_posts(site, user_id, service, specific_post_id=post_id)
            if not posts:
                self.log("CK_NO_POST_FOUND_FOR_ID")
                return

            current_post = posts[0]
            media_urls = self.process_post(current_post, site)

            current_post_id = current_post.get("id") or post_id or "unknown_id"
            title = current_post.get("title") or ""
            published_time = current_post.get("published") or ""

            self.total_files = len(media_urls)
            self.completed_files = 0
            futures = []

            for media_url in media_urls:
                if self.download_mode == "queue":
                    self.process_media_element(
                        media_url,
                        user_id,
                        post_id=current_post_id,
                        post_name=title,
                        post_time=published_time,
                        download_id=media_url,
                    )
                else:
                    future = self.executor.submit(
                        self.process_media_element,
                        media_url,
                        user_id,
                        current_post_id,
                        title,
                        published_time,
                        media_url,
                    )
                    futures.append(future)

            self.futures = futures

            if self.download_mode == "multi":
                for future in as_completed(futures):
                    if self.cancel_requested.is_set():
                        break
                    future.result()

        except Exception as e:
            self.log("CK_ERROR_DURING_DOWNLOAD", error=e)
        finally:
            self.shutdown_executor()