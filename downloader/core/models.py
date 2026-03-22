from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MediaEntry:
    url: str
    post_id: Optional[str] = None
    post_title: str = ""
    post_time: str = ""
    attachment_index: int = 1


@dataclass
class PostEntry:
    post_id: str
    title: str = ""
    published: str = ""
    media_urls: List[str] = field(default_factory=list)