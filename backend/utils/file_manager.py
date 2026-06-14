import os
import time
from pathlib import Path

from config import settings


def get_temp_path(filename: str) -> str:
    return os.path.join(settings.temp_dir, filename)


def get_thumbnail_path(filename: str) -> str:
    return os.path.join(settings.thumbnail_dir, filename)


def delete_file(path: str) -> None:
    try:
        os.remove(path) if os.path.exists(path) else None
    except Exception:
        pass


def cleanup_old_files(directory: str = None, older_than_hours: int = 24) -> int:
    target = directory or settings.temp_dir
    cutoff = time.time() - (older_than_hours * 3600)
    count = 0
    for f in Path(target).iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            count += 1
    return count
