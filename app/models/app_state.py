from dataclasses import dataclass, field
from typing import Optional, Any, Dict


@dataclass
class AppState:
    download_folder: str = ""
    language: str = "en"
    current_downloader: Optional[Any] = None
    current_download_thread: Optional[Any] = None
    download_start_time: Optional[float] = None
    is_downloading: bool = False
    is_cancel_requested: bool = False
    github_stars: Optional[int] = None
    update_info: Dict = field(default_factory=dict)