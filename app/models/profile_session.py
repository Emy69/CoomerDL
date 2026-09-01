import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from app.models.download_request import DownloadRequest

# Default for the "max_profiles_per_session" setting; the effective
# limit is user-configurable in Settings.
DEFAULT_MAX_PROFILES_PER_SESSION = 3


class ProfileStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = {
    ProfileStatus.COMPLETED,
    ProfileStatus.ERROR,
    ProfileStatus.CANCELLED,
}


@dataclass
class ProfileQueueItem:
    url: str
    request: Optional[DownloadRequest] = None
    status: ProfileStatus = ProfileStatus.PENDING
    error_reason: str = ""


class ProfileSession:
    """One download session over a limited list of profiles.

    Lives in memory only: it is never persisted to disk or settings and
    is not restored when the app restarts.
    """

    def __init__(self, items: List[ProfileQueueItem]):
        self.items = list(items)
        self.current_index = -1
        self.cancel_requested = threading.Event()
