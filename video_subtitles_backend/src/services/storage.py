from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import UploadFile


MEDIA_BASE = Path("media")
VIDEO_DIR = MEDIA_BASE / "videos"
SUBTITLE_DIR = MEDIA_BASE / "subtitles"


def ensure_media_dirs() -> None:
    """Ensure base media storage directories exist."""
    for d in (MEDIA_BASE, VIDEO_DIR, SUBTITLE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str) -> str:
    """Return a basic filesystem-safe filename."""
    return "".join(c for c in name if c.isalnum() or c in (" ", ".", "-", "_")).strip().replace(" ", "_")


# PUBLIC_INTERFACE
def build_unique_path(directory: Path, base_name: str, ext: str, prefix: Optional[str] = None) -> Path:
    """Build a unique file path avoiding collisions inside the directory.

    Args:
        directory: Target directory where the file will be placed.
        base_name: Base file name (without extension), will be sanitized.
        ext: File extension including leading dot.
        prefix: Optional string to prefix the filename (e.g., video_id).

    Returns:
        A Path object that does not currently exist in the filesystem.
    """
    safe_base = _safe_filename(base_name) or "file"
    if prefix:
        stem = f"{prefix}_{safe_base}"
    else:
        stem = safe_base

    candidate = directory / f"{stem}{ext}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}_{counter}{ext}"
        counter += 1
    return candidate


async def _iter_upload_chunks(file: UploadFile, chunk_size: int = 1024 * 1024) -> AsyncIterator[bytes]:
    """Async iterator to read chunks from an UploadFile."""
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        yield chunk


# PUBLIC_INTERFACE
async def save_upload_file(file: UploadFile, dest_path: Path, chunk_size: int = 1024 * 1024) -> None:
    """Persist an UploadFile to disk at the given destination path.

    The destination directory must already exist.

    Args:
        file: FastAPI UploadFile to save.
        dest_path: Destination path for saving the file.
        chunk_size: Chunk size for reading and writing.
    """
    # Make sure parent exists (defensive)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with dest_path.open("wb") as out:
            async for chunk in _iter_upload_chunks(file, chunk_size=chunk_size):
                out.write(chunk)
    finally:
        await file.close()


# PUBLIC_INTERFACE
def get_video_dir() -> Path:
    """Return the directory where videos are stored."""
    return VIDEO_DIR


# PUBLIC_INTERFACE
def get_subtitle_dir() -> Path:
    """Return the directory where subtitles are stored."""
    return SUBTITLE_DIR
