from dataclasses import dataclass


@dataclass
class DownloadRequest:
    url: str
    download_folder: str
    download_images: bool = True
    download_videos: bool = True
    download_compressed: bool = False
    create_subfolders: bool = True
    profile_name: str = ""
    max_downloads: int = 3