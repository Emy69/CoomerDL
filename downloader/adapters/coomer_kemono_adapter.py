from urllib.parse import quote_plus, urlencode, urljoin


class CoomerKemonoAdapter:
    def __init__(self, session, headers=None, log_callback=None, tr=None):
        self.session = session
        self.headers = headers or {}
        self.log_callback = log_callback
        self.tr = tr

    def translate(self, key, **kwargs):
        if callable(self.tr):
            try:
                return self.tr(key, **kwargs)
            except TypeError:
                text = self.tr(key)
                if kwargs:
                    try:
                        return text.format(**kwargs)
                    except Exception:
                        return text
                return text

        if kwargs:
            try:
                return key.format(**kwargs)
            except Exception:
                return key
        return key

    def log(self, message):
        domain = getattr(self, "site_name", "coomer")
        if self.log_callback:
            self.log_callback(domain, message)

    def fetch_user_posts(
        self,
        site,
        user_id,
        service,
        query=None,
        specific_post_id=None,
        initial_offset=0,
        log_fetching=True,
        only_first_page=False,
        cancel_event=None,
    ):
        all_posts = []
        offset = initial_offset
        user_id_encoded = quote_plus(user_id)

        while True:
            if cancel_event and cancel_event.is_set():
                return all_posts

            api_url = f"https://{site}/api/v1/{service}/user/{user_id_encoded}/posts"
            url_query = {"o": offset}
            if query not in (None, "", 0, "0"):
                url_query["q"] = query
            api_url += "?" + urlencode(url_query)

            self.site_name = "kemono" if "kemono" in site else "coomer"

            if log_fetching:
                self.log(self.translate("CK_FETCHING_USER_POSTS", api_url=api_url))

            try:
                response = self.session.get(api_url, headers=self.headers)
                if response.status_code == 400:
                    self.log(self.translate("CK_END_OF_POSTS_AT_OFFSET", offset=offset))
                    break

                response.raise_for_status()
                posts_data = response.json()

                if isinstance(posts_data, dict) and "data" in posts_data:
                    posts = posts_data["data"]
                else:
                    posts = posts_data

                if not posts:
                    break

                if specific_post_id:
                    post = next((p for p in posts if p["id"] == specific_post_id), None)
                    if post:
                        return [post]

                all_posts.extend(posts)
                offset += 50

                if only_first_page and not specific_post_id:
                    break

            except Exception as e:
                self.log(self.translate("CK_ERROR_FETCHING_USER_POSTS", error=e))
                break

        if specific_post_id:
            return [post for post in all_posts if post["id"] == specific_post_id]

        return all_posts

    def fetch_single_post(self, site, post_id, service):
        self.site_name = "kemono" if "kemono" in site else "coomer"
        api_url = f"https://{site}/api/v1/{service}/post/{post_id}"
        self.log(self.translate("CK_FETCHING_POST", api_url=api_url))

        try:
            response = self.session.get(api_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log(self.translate("CK_ERROR_FETCHING_POST", error=e))
            return None

    def extract_media_urls(self, post, site):
        base = f"https://{site}/"

        def _full(path):
            if not path:
                return None
            p = path if str(path).startswith("/") else f"/{path}"
            return urljoin(base, p)

        media_urls = []

        main_file = post.get("file") or {}
        u = _full(main_file.get("path") or main_file.get("url") or main_file.get("name"))
        if u:
            media_urls.append(u)

        for att in (post.get("attachments") or []):
            u = _full(att.get("path") or att.get("url") or att.get("name"))
            if u:
                media_urls.append(u)

        return media_urls