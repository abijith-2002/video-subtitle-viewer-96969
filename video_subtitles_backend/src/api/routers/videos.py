from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Iterator
import zlib

from fastapi import APIRouter, File, HTTPException, Path as FPath, Query, UploadFile, Request
from fastapi.responses import StreamingResponse, JSONResponse

from src.api.schemas import ErrorResponse, VideoListItem, VideoOut, SubtitleOut
from src.services.storage import ensure_media_dirs, get_video_dir, build_unique_path, save_upload_file, get_subtitle_dir
from src.services.validators import VIDEO_EXTENSIONS, has_allowed_extension, get_extension

router = APIRouter(prefix="/videos", tags=["Videos"])

METADATA_EXT = ".json"


def _parse_id_from_stem(stem: str) -> Optional[int]:
    """Try to parse a leading numeric ID from a file stem like '12_myvideo'."""
    first = stem.split("_", 1)[0]
    try:
        return int(first)
    except Exception:
        return None


def _hash_id_for_file(path: Path) -> int:
    """Derive a deterministic positive integer ID from the filename when no prefix exists."""
    # Use lowercase stem + extension to avoid case differences; CRC32 -> 0..2^32-1
    raw = (path.name).encode("utf-8", errors="ignore")
    val = zlib.crc32(raw) & 0xFFFFFFFF
    # Avoid zero id which can be ambiguous; shift into 1.. range
    return val or 1


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fs_times(p: Path) -> tuple[Optional[datetime], Optional[datetime]]:
    try:
        st = p.stat()
        created = datetime.fromtimestamp(getattr(st, "st_ctime", st.st_mtime))
        updated = datetime.fromtimestamp(st.st_mtime)
        return created, updated
    except Exception:
        return None, None


def _collect_subtitles_for_video(video_id: int, request: Optional[Request]) -> List[SubtitleOut]:
    subs_dir = get_subtitle_dir()
    items: List[SubtitleOut] = []
    for sub_path in subs_dir.glob(f"{video_id}_*.*"):
        sub_meta = _read_json(sub_path.with_suffix(METADATA_EXT))
        lang = sub_meta.get("language") or "en"
        sid = _parse_id_from_stem(sub_path.stem) or 0
        created, updated = _fs_times(sub_path)
        items.append(
            SubtitleOut(
                id=sid,
                language=lang,
                video_id=video_id,
                file_path=str(sub_path),
                created_at=created,
                updated_at=updated,
                file_url=(str(request.url_for("get_subtitle_file", subtitle_id=sid)) if request else None),
            )
        )
    # Sort by created_at then filename
    items.sort(key=lambda s: (s.created_at or datetime.min, s.file_path))
    return items


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[VideoListItem],
    summary="List videos",
    description="Returns a list of available videos without heavy fields.",
    responses={404: {"model": ErrorResponse}},
)
async def list_videos(
    q: Optional[str] = Query(default=None, description="Optional search string to filter by title"),
):
    """List videos by scanning media/videos; sidecar metadata is optional.
    Fallbacks:
    - title from filename
    - deterministic ID from filename when no numeric prefix exists
    """
    ensure_media_dirs()
    vids_dir = get_video_dir()
    items: List[VideoListItem] = []
    for path in vids_dir.iterdir():
        if not path.is_file():
            continue
        # Accept allowed video extensions
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        meta = _read_json(path.with_suffix(METADATA_EXT))
        # Fallback metadata from filename
        title = meta.get("title") or path.stem
        desc = meta.get("description")
        vid = _parse_id_from_stem(path.stem)
        if vid is None:
            vid = _hash_id_for_file(path)
        created, updated = _fs_times(path)
        if q and q.lower() not in title.lower():
            continue
        items.append(
            VideoListItem(
                id=vid,
                title=title,
                description=desc,
                created_at=created,
                updated_at=updated,
            )
        )
    # Sort newest first
    items.sort(key=lambda x: (x.created_at or datetime.min), reverse=True)
    return items


# PUBLIC_INTERFACE
@router.get(
    "/{video_id}",
    response_model=VideoOut,
    summary="Get video details",
    description="Retrieve full video details including associated subtitles.",
    responses={
        404: {"model": ErrorResponse, "description": "Video not found"},
    },
)
def _resolve_video_path_by_id(video_id: int, vids_dir: Path) -> Optional[Path]:
    """Resolve a video path by either leading numeric id prefix or deterministic hash of filename."""
    # First try numeric prefix
    prefix_matches = list(vids_dir.glob(f"{video_id}_*.*"))
    for p in prefix_matches:
        if p.suffix.lower() in VIDEO_EXTENSIONS and p.is_file():
            return p
    # Fallback: scan files and compute hash-based ids
    for p in vids_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if _hash_id_for_file(p) == video_id:
            return p
    return None


async def get_video(
    video_id: int = FPath(..., description="ID of the video"),
    request: Request = None,
):
    """Get a single video by ID from filesystem and include subtitles."""
    ensure_media_dirs()
    vids_dir = get_video_dir()
    path = _resolve_video_path_by_id(video_id, vids_dir)
    if path is None:
        raise HTTPException(status_code=404, detail="Video not found")
    meta = _read_json(path.with_suffix(METADATA_EXT))
    title = meta.get("title") or path.stem
    desc = meta.get("description")
    created, updated = _fs_times(path)
    subs = _collect_subtitles_for_video(video_id, request)
    return VideoOut(
        id=video_id,
        title=title,
        description=desc,
        file_path=str(path),
        created_at=created,
        updated_at=updated,
        subtitles=subs,
        stream_url=str(request.url_for("stream_video", video_id=video_id)) if request else None,
    )


# PUBLIC_INTERFACE
@router.post(
    "/upload",
    response_model=VideoOut,
    summary="Upload a new video",
    description="Upload a video file and create metadata sidecar on filesystem.",
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def upload_video(
    title: str = Query(..., description="Title for the uploaded video"),
    description: Optional[str] = Query(default=None, description="Optional description"),
    file: UploadFile = File(..., description="Binary video file to upload"),
    request: Request = None,
):
    """Upload a video file; filename format is '<id>_<safe-title>.<ext>' with id auto-incremented from existing files."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

    ensure_media_dirs()

    if not has_allowed_extension(file.filename, VIDEO_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Unsupported video format")

    ext = get_extension(file.filename)
    # Derive next numeric ID by scanning existing numeric-prefixed files only
    vids_dir = get_video_dir()
    max_id = 0
    for p in vids_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        vid = _parse_id_from_stem(p.stem)
        if vid and vid > max_id:
            max_id = vid
    new_id = max_id + 1

    # Build filename with id prefix using build_unique_path for collision safety
    base_name = f"{new_id}_{title}"
    dest_path = build_unique_path(vids_dir, base_name=base_name, ext=ext)

    # Save file to disk
    await save_upload_file(file, dest_path)

    # Sidecar metadata JSON
    meta = {
        "id": new_id,
        "title": title,
        "description": description,
        "file_path": str(dest_path),
    }
    _write_json(dest_path.with_suffix(METADATA_EXT), meta)

    # Build and return details
    return await get_video(video_id=new_id, request=request)


# PUBLIC_INTERFACE
@router.get(
    "/{video_id}/stream",
    summary="Stream video content",
    description="Stream the binary contents of a video file by ID.",
    responses={404: {"model": ErrorResponse}},
)
async def stream_video(
    video_id: int = FPath(..., description="ID of the video to stream"),
    request: Request = None,
):
    """Return a streaming response for the video file with HTTP Range support (filesystem-based)."""
    ensure_media_dirs()
    vids_dir = get_video_dir()
    path = _resolve_video_path_by_id(video_id, vids_dir)
    if path is None:
        raise HTTPException(status_code=404, detail="Video not found")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file missing on server")

    file_size = path.stat().st_size
    range_header = request.headers.get("range") if request else None

    def iter_file(start: int, end: int) -> Iterator[bytes]:
        with path.open("rb") as f:
            f.seek(start)
            remaining = end - start + 1
            chunk_size = 1024 * 1024
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        # Allow CORS and Range requests from browsers
        "Accept-Ranges": "bytes",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Range, Origin, Content-Type, Accept",
        "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges",
    }

    if range_header:
        # Example: "bytes=0-1023"
        try:
            units, _, range_spec = range_header.partition("=")
            if units != "bytes":
                raise ValueError("Only 'bytes' unit is supported")
            start_str, _, end_str = range_spec.partition("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            # Clamp values
            start = max(0, start)
            end = min(file_size - 1, end)
            if start > end or start >= file_size:
                # Invalid or out-of-range request
                return JSONResponse(
                    status_code=416,
                    content={"detail": "Requested Range Not Satisfiable"},
                    headers={
                        **headers,
                        "Content-Range": f"bytes */{file_size}",
                    },
                )
            content_length = end - start + 1
            resp = StreamingResponse(
                iter_file(start, end),
                media_type="video/mp4",
                status_code=206,
            )
            resp.headers.update(headers)
            resp.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            resp.headers["Content-Length"] = str(content_length)
            return resp
        except Exception:
            # Fallback to full content on malformed Range
            pass

    # No Range provided - send full file
    resp = StreamingResponse(iter_file(0, file_size - 1), media_type="video/mp4", status_code=200)
    resp.headers.update(headers)
    resp.headers["Content-Length"] = str(file_size)
    return resp
