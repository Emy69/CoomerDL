import threading

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
            max_downloads=getattr(self.app, "max_downloads", 3),
            only_this_url=bool(self.app.only_this_url_check.get()),
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

        parsed = self.app.url_service.parse_download_url(request.url)
        download_thread = None

        if parsed.site_type == "erome":
            self.app.add_log_message_safe(self.app.tr("Descargando Erome"))
            self.app.setup_erome_downloader(is_profile_download=parsed.is_profile)
            self.app.active_downloader = self.app.erome_downloader

            if parsed.is_album:
                self.app.add_log_message_safe(self.app.tr("URL del álbum"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(
                        self.app.active_downloader.process_album_page,
                        request.url,
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
                        request.url,
                        request.download_folder,
                        request.download_images,
                        request.download_videos,
                    ),
                    daemon=True
                )

        elif parsed.site_type == "bunkr":
            self.app.add_log_message_safe(self.app.tr("Descargando Bunkr"))
            self.app.setup_bunkr_downloader()
            self.app.active_downloader = self.app.bunkr_downloader

            if parsed.is_post:
                self.app.add_log_message_safe(self.app.tr("URL del post"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.app.bunkr_downloader.descargar_post_bunkr, request.url),
                    daemon=True
                )
            else:
                self.app.add_log_message_safe(self.app.tr("URL del perfil"))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.app.bunkr_downloader.descargar_perfil_bunkr, request.url),
                    daemon=True
                )

        elif parsed.site_type == "coomer_kemono":
            self.app.add_log_message_safe(self.app.tr("Iniciando descarga..."))
            self.app.setup_general_downloader()
            self.app.active_downloader = self.app.general_downloader

            site = f"{parsed.parsed_url.netloc}"
            service = parsed.service
            user = parsed.user
            post = parsed.post

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

            if parsed.is_post:
                self.app.add_log_message_safe(self.app.tr("Descargando post único..."))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(self.start_ck_post_download, site, service, user, post),
                    daemon=True
                )
            else:
                self.app.add_log_message_safe(self.app.tr("Descargando todo el contenido del usuario..."))
                download_thread = threading.Thread(
                    target=self.wrapped_download,
                    args=(
                        self.start_ck_profile_download,
                        site,
                        service,
                        user,
                        parsed.query,
                        True,
                        parsed.offset,
                        request.only_this_url,
                    ),
                    daemon=True
                )

        elif parsed.site_type == "simpcity":
            self.app.add_log_message_safe(self.app.tr("Descargando SimpCity"))
            self.app.setup_simpcity_downloader()
            self.app.active_downloader = self.app.simpcity_downloader
            download_thread = threading.Thread(
                target=self.wrapped_download,
                args=(
                    self.app.active_downloader.download_images_from_simpcity,
                    request.url,
                    not request.only_this_url,
                ),
                daemon=True
            )

        elif parsed.site_type == "jpg5":
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

    def start_ck_profile_download(self, site, service, user, query, download_all, initial_offset, only_this_url=False):
        download_info = self.app.active_downloader.download_media(
            site,
            user,
            service,
            query=query,
            download_all=download_all,
            initial_offset=initial_offset,
            only_first_page=only_this_url,
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