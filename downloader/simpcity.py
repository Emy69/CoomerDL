import os
import json
import re
import queue
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import cloudscraper
from concurrent.futures import ThreadPoolExecutor

class SimpCity:
    def __init__(self, download_folder, max_workers=5, log_callback=None, enable_widgets_callback=None, update_progress_callback=None, update_global_progress_callback=None, tr=None):
        self.download_folder = download_folder
        self.max_workers = max_workers
        self.descargadas = set()
        self.log_callback = log_callback
        self.enable_widgets_callback = enable_widgets_callback
        self.update_progress_callback = update_progress_callback
        self.update_global_progress_callback = update_global_progress_callback
        self.cancel_requested = False
        self.total_files = 0
        self.completed_files = 0
        self.download_queue = queue.Queue()
        self.scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        self.tr = tr

        # Selectors from original crawler
        self.title_selector = "h1[class=p-title-value]"
        self.posts_selector = "div[class*=message-main]"
        self.post_content_selector = "div[class*=message-userContent]"
        self.images_selector = "img[class*=bbImage]"
        self.videos_selector = "video source"
        self.iframe_selector = "iframe[class=saint-iframe]"
        self.attachments_block_selector = "section[class=message-attachments]"
        self.attachments_selector = "a"
        self.next_page_selector = "a[class*=pageNav-jump--next]"
        self.cookies_path = "resources/config/cookies/simpcity.json"
        self.set_cookies()

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def sanitize_folder_name(self, name):
        return re.sub(r'[<>:"/\\|?*]', '_', name)
    
    def set_cookies(self):
        if os.path.exists(self.cookies_path):
            with open(self.cookies_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            if isinstance(cookies, dict):
                cookies = [cookies]

            for c in cookies:
                if isinstance(c, dict) and "name" in c and "value" in c:
                    self.scraper.cookies.set(c["name"], c["value"])

    def fetch_page(self, url):
        try:
            response = self.scraper.get(url)
            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
            else:
                self.log(self.tr(f"Error: {response.status_code} al acceder a {url}"))
                return None
        except Exception as e:
            self.log(self.tr(f"Error al acceder a {url}: {e}"))
            return None

    def save_file(self, file_url, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        response = self.scraper.get(file_url, stream=True)
        if response.status_code == 200:
            with open(path, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            self.log(self.tr(f"Archivo descargado: {path}"))
        else:
            self.log(self.tr(f"Error al descargar {file_url}: {response.status_code}"))

    def process_post(self, post_content, download_folder):
        # Procesar imágenes
        images = post_content.select(self.images_selector)
        for img in images:
            src = img.get('src')
            if src:
                file_name = os.path.basename(urlparse(src).path)
                file_path = os.path.join(download_folder, file_name)
                self.save_file(src, file_path)

        # Procesar videos
        videos = post_content.select(self.videos_selector)
        for video in videos:
            src = video.get('src')
            if src:
                file_name = os.path.basename(urlparse(src).path)
                file_path = os.path.join(download_folder, file_name)
                self.save_file(src, file_path)

        # Procesar archivos adjuntos
        attachments_block = post_content.select_one(self.attachments_block_selector)
        if attachments_block:
            attachments = attachments_block.select(self.attachments_selector)
            for attachment in attachments:
                href = attachment.get('href')
                if href:
                    file_name = os.path.basename(urlparse(href).path)
                    file_path = os.path.join(download_folder, file_name)
                    self.save_file(href, file_path)

    def process_page(self, url):
        soup = self.fetch_page(url)
        if not soup:
            return

        title_element = soup.select_one(self.title_selector)
        folder_name = self.sanitize_folder_name(title_element.text.strip()) if title_element else 'SimpCity_Download'
        download_folder = os.path.join(self.download_folder, folder_name)
        os.makedirs(download_folder, exist_ok=True)

        message_inners = soup.select(self.posts_selector)
        for post in message_inners:
            post_content = post.select_one(self.post_content_selector)
            if post_content:
                self.process_post(post_content, download_folder)

        next_page = soup.select_one(self.next_page_selector)
        if next_page:
            next_page_url = next_page.get('href')
            if next_page_url:
                self.process_page(self.base_url + next_page_url)

    def download_images_from_simpcity(self, url):
        self.log(self.tr(f"Procesando hilo: {url}"))
        self.process_page(url)
        self.log(self.tr("Descarga completada."))
