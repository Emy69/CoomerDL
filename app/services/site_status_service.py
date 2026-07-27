from concurrent.futures import ThreadPoolExecutor

import requests


class SiteStatusService:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Referer": "https://coomer.st/",
        "Accept": "text/css",
    }

    SITES = [
        {
            "name": "Coomer",
            "host": "coomer.st",
            "check_url": "https://coomer.st/api/v1/onlyfans/user/belledelphine/posts?o=0",
            "alternative": "coomerfans.com",
        },
        {
            "name": "Kemono",
            "host": "kemono.cr",
            "check_url": "https://kemono.cr/api/v1/patreon/user/3295915/posts?o=0",
            "alternative": "pawchive.pw",
        },
    ]

    def __init__(self, timeout=10):
        self.timeout = timeout

    def _fetch_posts(self, check_url):
        response = requests.get(check_url, headers=self.HEADERS, timeout=self.timeout)
        if response.status_code != 200:
            return None

        data = response.json()
        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        return data or None

    def _first_file_path(self, posts):
        for post in posts:
            main_file = post.get("file") or {}
            if main_file.get("path"):
                return main_file["path"]

            for attachment in (post.get("attachments") or []):
                if attachment.get("path"):
                    return attachment["path"]

        return None

    def is_site_online(self, site) -> bool:
        try:
            posts = self._fetch_posts(site["check_url"])
            if not posts:
                return False

            file_path = self._first_file_path(posts)
            if not file_path:
                return False

            file_url = f"https://{site['host']}/data{file_path}"
            response = requests.get(
                file_url,
                headers=self.HEADERS,
                timeout=self.timeout,
                stream=True,
            )
            if response.status_code != 200:
                return False

            first_chunk = next(response.iter_content(8192), b"")
            return bool(first_chunk)
        except Exception:
            return False

    def get_offline_sites(self):
        with ThreadPoolExecutor(max_workers=len(self.SITES)) as executor:
            results = list(executor.map(self.is_site_online, self.SITES))

        return [site for site, online in zip(self.SITES, results) if not online]
