import os
import datetime
from pathlib import Path
from concurrent.futures import as_completed

from downloader.core.base_api_downloader import BaseApiDownloader
from downloader.adapters.erome_adapter import EromeAdapter


class EromeDownloader(BaseApiDownloader):
    def __init__(
        self,
        log_callback=None,
        enable_widgets_callback=None,
        update_progress_callback=None,
        update_global_progress_callback=None,
        download_images=True,
        download_videos=True,
        headers=None,
        language="en",
        is_profile_download=False,
        direct_download=False,
        tr=None,
        max_workers=5,
        download_folder="downloads",
    ):
        super().__init__(
            download_folder=download_folder,
            max_workers=max_workers,
            log_callback=log_callback,
            enable_widgets_callback=enable_widgets_callback,
            update_progress_callback=update_progress_callback,
            update_global_progress_callback=update_global_progress_callback,
            headers=headers,
            download_images=download_images,
            download_videos=download_videos,
            download_compressed=False,
            tr=tr,
        )

        self.language = language
        self.is_profile_download = is_profile_download
        self.direct_download = direct_download
        self.log_messages = []

        self.adapter = EromeAdapter(
            session=self.session,
            headers=self.headers,
            log_callback=self._capture_log,
            tr=self.tr,
        )

    def _capture_log(self, message):
        self.log_messages.append(message)
        if self.log_callback:
            self.log_callback(message)

    def log(self, message):
        self.log_messages.append(self.tr(message) if self.tr else message)
        if self.log_callback:
            self.log_callback(self.tr(message) if self.tr else message)

    def request_cancel(self):
        self.cancel_requested.set()
        self.log("Download cancelled")
        if self.is_profile_download and self.enable_widgets_callback:
            self.enable_widgets_callback()

    def _download_entries(self, media_entries, root_folder):
        self.total_files = len(media_entries)
        self.completed_files = 0
        futures = []

        for entry in media_entries:
            media_url = entry["media_url"]
            folder_name = entry.get("folder_name") or "erome_album"
            target_folder = os.path.join(root_folder, folder_name) if not os.path.isabs(folder_name) else folder_name

            os.makedirs(target_folder, exist_ok=True)

            if self.download_mode == "queue":
                self.process_media_element(
                    media_url,
                    user_id=None,
                    post_id=entry.get("post_id"),
                    post_name=entry.get("title"),
                    post_time=entry.get("published"),
                    download_id=media_url,
                    target_folder=target_folder,
                    forced_filename=entry.get("filename"),
                )
            else:
                future = self.executor.submit(
                    self.process_media_element,
                    media_url,
                    user_id=None,
                    post_id=entry.get("post_id"),
                    post_name=entry.get("title"),
                    post_time=entry.get("published"),
                    download_id=media_url,
                    target_folder=target_folder,
                    forced_filename=entry.get("filename"),
                )
                futures.append(future)

        self.futures = futures

        if self.download_mode == "multi":
            for future in as_completed(futures):
                if self.cancel_requested.is_set():
                    self.log("Cancelling remaining downloads.")
                    break
                future.result()

    def process_album_page(self, page_url, base_folder, download_images=True, download_videos=True):
        try:
            if self.cancel_requested.is_set():
                return

            self._capture_log(self.tr("Processing album URL: {page_url}", page_url=page_url))
            resolved = self.adapter._resolve_album(
                page_url,
                download_images=download_images,
                download_videos=download_videos,
                direct_download=self.direct_download,
            )

            self._download_entries(resolved["media"], base_folder)
            self._capture_log(self.tr("Album download complete: {folder_name}", folder_name=resolved["folder_name"]))

        except Exception as e:
            self._capture_log(self.tr("Error accessing page: {page_url}, status code: {status_code}", page_url=page_url, status_code=str(e)))
        finally:
            if not self.is_profile_download and self.enable_widgets_callback:
                self.enable_widgets_callback()
            self.export_logs()

    def process_profile_page(self, url, download_folder, download_images, download_videos):
        try:
            if self.cancel_requested.is_set():
                return

            self._capture_log(self.tr("Processing profile URL: {url}", url=url))
            resolved = self.adapter._resolve_profile(
                url,
                download_images=download_images,
                download_videos=download_videos,
                direct_download=self.direct_download,
            )

            self._download_entries(resolved["media"], download_folder)
            self._capture_log(self.tr("Profile download complete: {username}", username=resolved["folder_name"]))

        except Exception as e:
            self._capture_log(self.tr("Error accessing page: {url}, status code: {status_code}", url=url, status_code=str(e)))
        finally:
            if self.enable_widgets_callback:
                self.enable_widgets_callback()
            self.export_logs()

    def export_logs(self):
        log_folder = "resources/config/logs/"
        Path(log_folder).mkdir(parents=True, exist_ok=True)
        log_file_path = Path(log_folder) / f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(log_file_path, "w", encoding="utf-8") as file:
                file.write("\n".join(self.log_messages))
            if self.log_callback:
                self.log_callback(self.tr("Logs exported successfully to {path}", path=log_file_path))
        except Exception as e:
            if self.log_callback:
                self.log_callback(self.tr("Failed to export logs: {error}", error=e))