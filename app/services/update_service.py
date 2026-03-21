import requests


class UpdateService:
    def __init__(self, tr):
        self.tr = tr

    def get_github_stars(self, user: str, repo: str, timeout: float = 2.5) -> int:
        try:
            url = f"https://api.github.com/repos/{user}/{repo}"
            headers = {
                "User-Agent": "CoomerDL",
                "Accept": "application/vnd.github+json",
            }
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            return int(data.get("stargazers_count", 0))
        except Exception:
            return 0

    def parse_version_string(self, version_str):
        try:
            return tuple(int(p) for p in version_str[1:].split("."))
        except (ValueError, IndexError):
            return 0, 0, 0

    

    def is_offline_error(self, err: Exception) -> bool:
        s = str(err)
        return (
            isinstance(err, requests.exceptions.ConnectionError)
            or "NameResolutionError" in s
            or "getaddrinfo failed" in s
            or "Failed to establish a new connection" in s
            or "Max retries exceeded" in s
        )