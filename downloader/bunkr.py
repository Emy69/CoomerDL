import os
from concurrent.futures import as_completed

from downloader.core.base_api_downloader import BaseApiDownloader
from downloader.adapters.bunkr_adapter import BunkrAdapter


class BunkrDownloader(BaseApiDownloader):
    def __init__(self, *args, translations=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.translations = translations or {}
        self.adapter = BunkrAdapter(
            session=self.session,
            headers=self.headers,
            log_callback=self.log_callback,
            tr=self._translate_message,
        )

    def _translate_message(self, key):
        return self.translations.get(key, key)

    def descargar_post_bunkr(self, url_post):
        try:
            self.log(f"Starting Bunkr post download: {url_post}")

            resolved = self.adapter.resolve_url(url_post)
            folder_name = resolved["folder_name"]
            media_entries = resolved["media"]

            target_folder = os.path.join(self.download_folder, folder_name)
            os.makedirs(target_folder, exist_ok=True)

            self.total_files = len(media_entries)
            self.completed_files = 0
            futures = []

            for entry in media_entries:
                media_url = entry["media_url"]
                if self.download_mode == "queue":
                    self.process_media_element(
                        media_url,
                        user_id=None,
                        post_id=entry["post_id"],
                        post_name=entry["title"],
                        post_time=entry["published"],
                        download_id=media_url,
                        target_folder=target_folder,
                    )
                else:
                    future = self.executor.submit(
                        self.process_media_element,
                        media_url,
                        user_id=None,
                        post_id=entry["post_id"],
                        post_name=entry["title"],
                        post_time=entry["published"],
                        download_id=media_url,
                        target_folder=target_folder,
                    )
                    futures.append(future)

            self.futures = futures

            for future in as_completed(futures):
                if self.cancel_requested.is_set():
                    break
                future.result()

        except Exception as e:
            self.log(f"Error processing Bunkr post {url_post}: {e}")
        finally:
            self.shutdown_executor()

    def descargar_perfil_bunkr(self, url_perfil):
        try:
            self.log(f"Starting Bunkr profile download: {url_perfil}")

            resolved = self.adapter.resolve_url(url_perfil)
            folder_name = resolved["folder_name"]
            media_entries = resolved["media"]

            target_folder = os.path.join(self.download_folder, folder_name)
            os.makedirs(target_folder, exist_ok=True)

            self.total_files = len(media_entries)
            self.completed_files = 0
            futures = []

            for entry in media_entries:
                media_url = entry["media_url"]
                if self.download_mode == "queue":
                    self.process_media_element(
                        media_url,
                        user_id=None,
                        post_id=entry["post_id"],
                        post_name=entry["title"],
                        post_time=entry["published"],
                        download_id=media_url,
                        target_folder=target_folder,
                    )
                else:
                    future = self.executor.submit(
                        self.process_media_element,
                        media_url,
                        user_id=None,
                        post_id=entry["post_id"],
                        post_name=entry["title"],
                        post_time=entry["published"],
                        download_id=media_url,
                        target_folder=target_folder,
                    )
                    futures.append(future)

            self.futures = futures

            for future in as_completed(futures):
                if self.cancel_requested.is_set():
                    break
                future.result()

        except Exception as e:
            self.log(f"Error processing Bunkr profile {url_perfil}: {e}")
        finally:
            self.shutdown_executor()

    def set_max_downloads(self, max_downloads):
        self.update_max_downloads(max_downloads)