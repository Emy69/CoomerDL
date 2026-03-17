import json
import os


class TranslationService:
    def __init__(self, language="en", locales_dir="resources/languages"):
        self.locales_dir = locales_dir
        self.language = language
        self.translations = {}
        self.load_translations(language)

    def load_translations(self, language=None):
        if language:
            self.language = language

        path = os.path.join(self.locales_dir, f"{self.language}.json")

        try:
            with open(path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except Exception:
            self.translations = {}

    def set_language(self, language):
        self.load_translations(language)

    def tr(self, key, **kwargs):
        text = self.translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text