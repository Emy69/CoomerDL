import datetime
import re
import threading
from urllib.parse import urlparse

from app.models.download_request import DownloadRequest


class MainController:
    def __init__(self, app):
        self.app = app

    def build_request_from_ui(self) -> DownloadRequest:
        return DownloadRequest(
            url=self.app.url_entry.get().strip(),
            download_folder=self.app.download_folder,
            download_images=bool(self.app.download_images_check.get()),
            download_videos=bool(self.app.download_videos_check.get()),
            download_compressed=bool(self.app.download_compressed_check.get()),
            max_downloads=getattr(self.app, "max_downloads", 3)
        )

    def start_download(self):
        request = self.build_request_from_ui()

        if not request.download_folder:
            self.app.show_error(
                self.app.tr("Error"),
                self.app.tr("Por favor, selecciona una carpeta de descarga.")
            )
            return

        if not request.url:
            self.app.show_error(
                self.app.tr("Error"),
                self.app.tr("Por favor, introduce una URL válida.")
            )
            return

        self.app.prepare_download_ui()

        url = request.url
        parsed_url = urlparse(url)
        download_thread = None

        if "erome.com" in url:
            self.app.add_log_message_safe(self.app.tr("Descargando Erome"))
            is_profile_download = "/a/" not in url
            self.app.setup_erome_downloader(is_profile_download=is_profile_download)
            self.app.active_downloader = self.app.erome_downloader

            if "/a/" in url:
                self.app.add_log_message_safe(self.app.tr("URL del álbum"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(
                        self.app.active_downloader.process_album_page,
                        url,
                        request.download_folder,
                        request.download_images,
                        request.download_videos,
                    ),
                    daemon=True
                )
            else:
                self.app.add_log_message_safe(self.app.tr("URL del perfil"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(
                        self.app.active_downloader.process_profile_page,
                        url,
                        request.download_folder,
                        request.download_images,
                        request.download_videos,
                    ),
                    daemon=True
                )

        elif re.search(r"https?://([a-z0-9-]+\.)?bunkr\.[a-z]{2,}", url):
            self.app.add_log_message_safe(self.app.tr("Descargando Bunkr"))
            self.app.setup_bunkr_downloader()
            self.app.active_downloader = self.app.bunkr_downloader

            if any(sub in url for sub in ["/v/", "/i/", "/f/"]):
                self.app.add_log_message_safe(self.app.tr("URL del post"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.app.bunkr_downloader.descargar_post_bunkr, url),
                    daemon=True
                )
            else:
                self.app.add_log_message_safe(self.app.tr("URL del perfil"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.app.bunkr_downloader.descargar_perfil_bunkr, url),
                    daemon=True
                )

        elif parsed_url.netloc in ["coomer.st", "kemono.cr"]:
            self.app.add_log_message_safe(self.app.tr("Iniciando descarga..."))
            self.app.setup_general_downloader()
            self.app.active_downloader = self.app.general_downloader

            site = f"{parsed_url.netloc}"
            service, user, post = self.app.extract_ck_parameters(parsed_url)

            if service is None or user is None:
                if service is None:
                    self.app.add_log_message_safe(self.app.tr("No se pudo extraer el servicio."))
                    self.app.show_error(self.app.tr("Error"), self.app.tr("No se pudo extraer el servicio."))
                else:
                    self.app.add_log_message_safe(self.app.tr("No se pudo extraer el ID del usuario."))
                    self.app.show_error(self.app.tr("Error"), self.app.tr("No se pudo extraer el ID del usuario."))

                self.app.add_log_message_safe(self.app.tr("URL no válida"))
                self.app.enable_widgets()
                return

            self.app.add_log_message_safe(
                self.app.tr("Servicio extraído: {service} del sitio: {site}", service=service, site=site)
            )

            if post is not None:
                self.app.add_log_message_safe(self.app.tr("Descargando post único..."))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.start_ck_post_download, site, service, user, post),
                    daemon=True
                )
            else:
                query, offset = self.app.extract_ck_query(parsed_url)
                self.app.add_log_message_safe(self.app.tr("Descargando todo el contenido del usuario..."))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.start_ck_profile_download, site, service, user, query, True, offset),
                    daemon=True
                )

        elif "simpcity.cr" in url:
            self.app.add_log_message_safe(self.app.tr("Descargando SimpCity"))
            self.app.setup_simpcity_downloader()
            self.app.active_downloader = self.app.simpcity_downloader
            download_thread = threading.Thread(
                target=self.wrapped_download,
                args=(self.app.active_downloader.download_images_from_simpcity, url),
                daemon=True
            )

        elif "jpg5.su" in url:
            self.app.add_log_message_safe(self.app.tr("Descargando desde Jpg5"))
            self.app.setup_jpg5_downloader()
            download_thread = threading.Thread(
                target=self.wrapped_download,
                args=(self.app.active_downloader.descargar_imagenes,),
                daemon=True
            )

        else:
            self.app.add_log_message_safe(self.app.tr("URL no válida"))
            self.app.enable_widgets()
            return

        if download_thread:
            download_thread.start()
            self.app.app_state.current_download_thread = download_thread

    def wrapped_download(self, download_method, *args):
        try:
            download_method(*args)
        finally:
            self.app.active_downloader = None
            self.app.enable_widgets()
            self.app.export_logs()

    def start_ck_profile_download(self, site, service, user, query, download_all, initial_offset):
        download_info = self.app.active_downloader.download_media(
            site,
            user,
            service,
            query=query,
            download_all=download_all,
            initial_offset=initial_offset
        )
        if download_info:
            self.app.add_log_message_safe(f"Download info: {download_info}")
        return download_info

    def start_ck_post_download(self, site, service, user, post):
        download_info = self.app.active_downloader.download_single_post(site, post, service, user)
        if download_info:
            self.app.add_log_message_safe(f"Download info: {download_info}")
        return download_info

    def cancel_download(self):
        if self.app.active_downloader:
            try:
                self.app.active_downloader.request_cancel()
            except Exception:
                pass
            self.app.active_downloader = None
            self.app.clear_progress_bars()
        else:
            self.app.add_log_message_safe(self.app.tr("No hay una descarga en curso para cancelar."))

        self.app.enable_widgets()