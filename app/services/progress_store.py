from dataclasses import dataclass
from typing import Optional

from app.models.progress_item import ProgressItem


@dataclass
class ProgressEntry:
    item: ProgressItem
    row: Optional[object] = None


class ProgressStore:
    def __init__(self):
        self._entries = {}

    def has(self, file_id) -> bool:
        return file_id in self._entries

    def get(self, file_id) -> Optional[ProgressEntry]:
        return self._entries.get(file_id)

    def set(self, file_id, entry: ProgressEntry):
        self._entries[file_id] = entry

    def remove(self, file_id):
        return self._entries.pop(file_id, None)

    def clear(self):
        self._entries.clear()

    def is_empty(self) -> bool:
        return len(self._entries) == 0

    def keys(self):
        return list(self._entries.keys())

    def values(self):
        return list(self._entries.values())

    def items(self):
        return list(self._entries.items())

    def get_item(self, file_id) -> Optional[ProgressItem]:
        entry = self.get(file_id)
        return entry.item if entry else None

    def get_row(self, file_id):
        entry = self.get(file_id)
        return entry.row if entry else None

    def set_row(self, file_id, row):
        entry = self.get(file_id)
        if entry:
            entry.row = row

    def set_item(self, file_id, item: ProgressItem):
        entry = self.get(file_id)
        if entry:
            entry.item = item