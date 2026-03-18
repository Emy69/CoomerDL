from dataclasses import dataclass
from typing import Optional


@dataclass
class ProgressItem:
    file_id: str
    file_path: str
    downloaded: int = 0
    total: int = 0
    speed: Optional[float] = None
    eta: Optional[float] = None
    status: Optional[str] = None