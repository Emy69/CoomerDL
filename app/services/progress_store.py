class ProgressStore:
    def __init__(self):
        self._rows = {}

    def has(self, file_id) -> bool:
        return file_id in self._rows

    def get(self, file_id):
        return self._rows.get(file_id)

    def set(self, file_id, row):
        self._rows[file_id] = row

    def remove(self, file_id):
        return self._rows.pop(file_id, None)

    def clear(self):
        self._rows.clear()

    def is_empty(self) -> bool:
        return len(self._rows) == 0

    def keys(self):
        return list(self._rows.keys())

    def values(self):
        return list(self._rows.values())

    def items(self):
        return list(self._rows.items())