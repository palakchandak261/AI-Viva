"""File utility helpers."""
import os
import uuid
from pathlib import Path


def ensure_dir(path: str) -> str:
    """Create directory if it doesn't exist and return the path."""
    os.makedirs(path, exist_ok=True)
    return path


def unique_filename(original_name: str) -> str:
    """Generate a UUID-based unique filename preserving the extension."""
    ext = Path(original_name).suffix
    return f"{uuid.uuid4().hex}{ext}"


def safe_delete(file_path: str) -> bool:
    """Delete a file safely, returning True if deleted."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except OSError:
        pass
    return False


def human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
