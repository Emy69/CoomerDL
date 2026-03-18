import os


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz"}


def get_file_icon_key(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in ARCHIVE_EXTENSIONS:
        return "zip"
    return "default"


def shorten_filename(file_path: str, max_length: int = 30) -> str:
    file_name = os.path.basename(file_path)
    if len(file_name) > max_length:
        return file_name[:max_length] + "..."
    return file_name


def format_eta(eta) -> str:
    if eta is None:
        return "ETA: N/A"
    return f"ETA: {int(eta // 60)}m {int(eta % 60)}s"


def format_speed(speed) -> str:
    if speed is None:
        return "Speed: 0 KB/s"
    if speed < 1_048_576:
        return f"Speed: {speed / 1024:.2f} KB/s"
    return f"Speed: {speed / 1_048_576:.2f} MB/s"


def format_progress_text(downloaded: int, total: int) -> str:
    if total <= 0:
        return "0%"
    percentage = (downloaded / total) * 100
    return f"{percentage:.2f}% ({downloaded / 1048576:.2f} MB / {total / 1048576:.2f} MB)"