from downloader.bunkr import BunkrDownloader
from downloader.downloader import Downloader
from downloader.erome import EromeDownloader
from downloader.jpg5 import Jpg5Downloader
from downloader.simpcity import SimpCity


class DownloaderFactory:
    def __init__(self, app):
        """
        app = instancia de ImageDownloaderApp
        La factory usa el estado actual de la app, pero saca la construcción
        de downloaders fuera de ui.py
        """
        self.app = app

    def create_erome_downloader(self, is_profile_download=False):
        return EromeDownloader(
            root=self.app,
            enable_widgets_callback=self.app.enable_widgets,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
                "Referer": "https://www.erome.com/"
            },
            log_callback=self.app.add_log_message_safe,
            update_progress_callback=self.app.update_progress,
            update_global_progress_callback=self.app.update_global_progress,
            download_images=self.app.download_images_check.get(),
            download_videos=self.app.download_videos_check.get(),
            is_profile_download=is_profile_download,
            max_workers=self.app.max_downloads,
            tr=self.app.tr
        )

    def create_simpcity_downloader(self):
        return SimpCity(
            download_folder=self.app.download_folder,
            log_callback=self.app.add_log_message_safe,
            enable_widgets_callback=self.app.enable_widgets,
            update_progress_callback=self.app.update_progress,
            update_global_progress_callback=self.app.update_global_progress,
            tr=self.app.tr
        )

    def create_bunkr_downloader(self):
        return BunkrDownloader(
            download_folder=self.app.download_folder,
            log_callback=self.app.add_log_message_safe,
            enable_widgets_callback=self.app.enable_widgets,
            update_progress_callback=self.app.update_progress,
            update_global_progress_callback=self.app.update_global_progress,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                "Referer": "https://bunkr.site/",
            },
            max_workers=self.app.max_downloads
        )

    def create_general_downloader(self):
        downloader = Downloader(
            download_folder=self.app.download_folder,
            log_callback=self.app.add_log_message_safe,
            enable_widgets_callback=self.app.enable_widgets,
            update_progress_callback=self.app.update_progress,
            update_global_progress_callback=self.app.update_global_progress,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                "Referer": "https://coomer.st/",
                "Accept": "text/css"
            },
            download_images=self.app.download_images_check.get(),
            download_videos=self.app.download_videos_check.get(),
            download_compressed=self.app.download_compressed_check.get(),
            tr=self.app.tr,
            max_workers=self.app.max_downloads,
            folder_structure=self.app.settings.get("folder_structure", "default")
        )
        downloader.file_naming_mode = self.app.settings.get("file_naming_mode", 0)
        return downloader

    def create_jpg5_downloader(self, url):
        return Jpg5Downloader(
            url=url,
            carpeta_destino=self.app.download_folder,
            log_callback=self.app.add_log_message_safe,
            tr=self.app.tr,
            progress_manager=self.app.progress_manager,
            max_workers=self.app.max_downloads
        )