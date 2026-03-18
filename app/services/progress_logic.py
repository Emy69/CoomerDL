class ProgressLogic:
    def is_completed(self, downloaded: int, total: int) -> bool:
        if total <= 0:
            return False
        return downloaded >= total

    def should_update_row(self, total: int) -> bool:
        return total > 0

    def should_keep_empty_message_hidden(self, has_rows: bool) -> bool:
        return has_rows

    def should_reset_footer(self, store_is_empty: bool) -> bool:
        return store_is_empty