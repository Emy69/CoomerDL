from app.interfaces.frontend_bridge import FrontendBridge
from typing import Optional

class PySideFrontendBridge(FrontendBridge):
    def __init__(self, app):
        self.app = app
        self._session_snapshot = None

    def begin_session_snapshot(
        self,
        download_folder: str,
        download_images: bool,
        download_videos: bool,
        download_compressed: bool,
    ):
        # Downloaders are created per profile from a worker thread; the
        # snapshot freezes what they read through the bridge so a session
        # never re-reads live UI state between profiles.
        self._session_snapshot = {
            "download_folder": download_folder,
            "download_images": bool(download_images),
            "download_videos": bool(download_videos),
            "download_compressed": bool(download_compressed),
        }

    def end_session_snapshot(self):
        self._session_snapshot = None

    def log(self, domain_or_message: str, message: Optional[str] = None):
        if message is None:
            self.app.add_log_message_safe(domain_or_message)
        else:
            self.app.add_log_message_safe(domain_or_message, message)

    def enable_widgets(self):
        self.app.enable_widgets()

    def update_progress(self, downloaded, total, file_id=None, file_path=None, speed=None, eta=None, status=None):
        self.app.update_progress(downloaded, total, file_id, file_path, speed, eta, status=status)

    def update_global_progress(self, completed_files, total_files):
        self.app.update_global_progress(completed_files, total_files)

    def get_download_folder(self) -> str:
        if self._session_snapshot is not None:
            return self._session_snapshot["download_folder"]
        return self.app.download_folder

    def get_max_downloads(self) -> int:
        return self.app.max_downloads

    def get_download_images(self) -> bool:
        if self._session_snapshot is not None:
            return self._session_snapshot["download_images"]
        return bool(self.app.download_images_check.get())

    def get_download_videos(self) -> bool:
        if self._session_snapshot is not None:
            return self._session_snapshot["download_videos"]
        return bool(self.app.download_videos_check.get())

    def get_download_compressed(self) -> bool:
        if self._session_snapshot is not None:
            return self._session_snapshot["download_compressed"]
        return bool(self.app.download_compressed_check.get())

    def get_tr(self):
        return self.app.tr