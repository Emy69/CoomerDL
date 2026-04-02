import threading

from downloader.bunkr import BunkrDownloader
from downloader.downloader import Downloader
from downloader.erome import EromeDownloader
from downloader.jpg5 import Jpg5Downloader
from downloader.simpcity import SimpCity


class DownloaderFactory:
    def __init__(self, frontend_bridge, app=None):
        self.frontend = frontend_bridge
        self.app = app

    def create_erome_downloader(self, is_profile_download=False):
        return EromeDownloader(
            enable_widgets_callback=self.frontend.enable_widgets,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
                "Referer": "https://www.erome.com/"
            },
            log_callback=self.frontend.log,
            update_progress_callback=self.frontend.update_progress,
            update_global_progress_callback=self.frontend.update_global_progress,
            download_images=self.frontend.get_download_images(),
            download_videos=self.frontend.get_download_videos(),
            is_profile_download=is_profile_download,
            max_workers=self.frontend.get_max_downloads(),
            tr=self.frontend.get_tr()
        )

    def create_simpcity_downloader(self):
        return SimpCity(
            download_folder=self.frontend.get_download_folder(),
            log_callback=self.frontend.log,
            enable_widgets_callback=self.frontend.enable_widgets,
            update_progress_callback=self.frontend.update_progress,
            update_global_progress_callback=self.frontend.update_global_progress,
            tr=self.frontend.get_tr()
        )

    def create_bunkr_downloader(self):
        return BunkrDownloader(
            download_folder=self.frontend.get_download_folder(),
            log_callback=self.frontend.log,
            enable_widgets_callback=self.frontend.enable_widgets,
            update_progress_callback=self.frontend.update_progress,
            update_global_progress_callback=self.frontend.update_global_progress,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                "Referer": "https://bunkr.site/",
            },
            max_workers=self.frontend.get_max_downloads(),
            tr=self.frontend.get_tr(),
        )

    def create_general_downloader(self, settings):
        downloader = Downloader(
            download_folder=self.frontend.get_download_folder(),
            log_callback=self.frontend.log,
            enable_widgets_callback=self.frontend.enable_widgets,
            update_progress_callback=self.frontend.update_progress,
            update_global_progress_callback=self.frontend.update_global_progress,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                "Referer": "https://coomer.st/",
                "Accept": "text/css"
            },
            download_images=self.frontend.get_download_images(),
            download_videos=self.frontend.get_download_videos(),
            download_compressed=self.frontend.get_download_compressed(),
            tr=self.frontend.get_tr(),
            max_workers=self.frontend.get_max_downloads(),
            folder_structure=settings.get("folder_structure", "default"),
            max_retries=int(settings.get("max_retries", 3) or 3),
            retry_interval=float(settings.get("retry_interval", 2.0) or 2.0),
            rate_limit_interval=float(settings.get("rate_limit_interval", 0.0) or 0.0),
        )
        downloader.file_naming_mode = settings.get("file_naming_mode", 0)
        return downloader

    def create_jpg5_downloader(self, url, progress_manager=None):
        return Jpg5Downloader(
            url=url,
            carpeta_destino=self.frontend.get_download_folder(),
            log_callback=self.frontend.log,
            tr=self.frontend.get_tr(),
            progress_manager=progress_manager,
            max_workers=self.frontend.get_max_downloads()
        )