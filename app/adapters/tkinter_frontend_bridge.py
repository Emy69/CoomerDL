from app.interfaces.frontend_bridge import FrontendBridge


class TkinterFrontendBridge(FrontendBridge):
    def __init__(self, app):
        self.app = app

    def log(self, message: str):
        self.app.add_log_message_safe(message)

    def enable_widgets(self):
        self.app.enable_widgets()

    def update_progress(self, downloaded, total, file_id=None, file_path=None, speed=None, eta=None, status=None):
        self.app.update_progress(downloaded, total, file_id, file_path, speed, eta, status=status)

    def update_global_progress(self, completed_files, total_files):
        self.app.update_global_progress(completed_files, total_files)

    def show_error(self, title: str, message: str):
        self.app.show_error(title, message)

    def get_download_folder(self) -> str:
        return self.app.download_folder

    def get_max_downloads(self) -> int:
        return self.app.max_downloads

    def get_download_images(self) -> bool:
        return bool(self.app.download_images_check.get())

    def get_download_videos(self) -> bool:
        return bool(self.app.download_videos_check.get())

    def get_download_compressed(self) -> bool:
        return bool(self.app.download_compressed_check.get())

    def get_tr(self):
        return self.app.tr