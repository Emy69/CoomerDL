import json
import os

from downloader.core import protected_json


class CookiesSettingsService:
    def __init__(self, cookies_path):
        self.cookies_path = cookies_path

    def ensure_parent_dir(self):
        os.makedirs(os.path.dirname(self.cookies_path), exist_ok=True)

    def _load(self):
        try:
            data = protected_json.load(self.cookies_path)
        except (OSError, ValueError):
            return None
        # Files from older versions are plain JSON; encrypt them in place.
        if data is not None and protected_json.available():
            try:
                with open(self.cookies_path, "r", encoding="utf-8") as f:
                    plain = not protected_json.is_protected(json.load(f))
                if plain:
                    protected_json.save(self.cookies_path, data)
            except (OSError, ValueError):
                pass
        return data

    def load_cookies_text(self) -> str:
        data = self._load()
        if isinstance(data, (dict, list)):
            return json.dumps(data, indent=4, ensure_ascii=False)
        return ""

    def parse_cookies_text(self, cookies_text: str):
        cookies_text = cookies_text.strip()
        if not cookies_text:
            return None

        return json.loads(cookies_text)

    def save_cookies_text(self, cookies_text: str):
        cookies_data = self.parse_cookies_text(cookies_text)
        protected_json.save(self.cookies_path, cookies_data)
        return cookies_data

    def count_cookies(self) -> int:
        data = self._load()
        if isinstance(data, (dict, list)):
            return len(data)
        return 0

    def clear_cookies(self):
        protected_json.save(self.cookies_path, {})

    def import_cookies_file(self, source_path: str) -> str:
        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()

        # validate before returning
        self.parse_cookies_text(content)
        return content