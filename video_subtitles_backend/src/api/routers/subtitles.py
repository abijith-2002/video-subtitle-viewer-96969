from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Path as FPath, Query, UploadFile
from fastapi.responses import FileResponse

from src.api.schemas import ErrorResponse, SubtitleOut
from src.services.storage import ensure_media_dirs, get_subtitle_dir, build_unique_path, save_upload_file
from src.services.validators import SUBTITLE_EXTENSIONS, has_allowed_extension, get_extension, is_valid_language_code

router = APIRouter(prefix="", tags=["Subtitles"])

METADATA_EXT = ".json"


def _parse_id_from_stem(stem: str) -> Optional[int]:
    first = stem.split("_", 1)[0]
    try:
        return int(first)
    except Exception:
        return None


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# PUBLIC_INTERFACE
@router.get(
    "/videos/{video_id}/subtitles",
    response_model=List[SubtitleOut],
    summary="List subtitles for a video",
    description="Returns all subtitles linked to the specified video.",
    responses={404: {"model": ErrorResponse}},
)
async def list_subtitles_for_video(
    video_id: int = FPath(..., description="Video ID"),
):
    ensure_media_dirs()
    subs_dir = get_subtitle_dir()
    subs: List[SubtitleOut] = []
    for p in subs_dir.glob(f"{video_id}_*.*"):
        sid = _parse_id_from_stem(p.stem) or 0
        meta = _read_json(p.with_suffix(METADATA_EXT))
        lang = meta.get("language") or "en"
        created_at = datetime.fromtimestamp(p.stat().st_ctime) if p.exists() else None
        updated_at = datetime.fromtimestamp(p.stat().st_mtime) if p.exists() else None
        subs.append(
            SubtitleOut(
                id=sid,
                language=lang,
                video_id=video_id,
                file_path=str(p),
                created_at=created_at,
                updated_at=updated_at,
            )
        )
    subs.sort(key=lambda s: (s.created_at or datetime.min, s.file_path))
    return subs


# PUBLIC_INTERFACE
@router.post(
    "/videos/{video_id}/subtitles",
    response_model=SubtitleOut,
    summary="Upload subtitle for a video",
    description="Upload a subtitle file (.vtt or .srt) and associate it with the specified video.",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def upload_subtitle_for_video(
    video_id: int = FPath(..., description="Video ID"),
    language: str = Query(..., description="Language code (e.g. en, es, fr)"),
    file: UploadFile = File(..., description="Subtitle file (.vtt or .srt)"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded subtitle must have a filename")
    if not is_valid_language_code(language):
        raise HTTPException(status_code=400, detail="Invalid language code")

    ensure_media_dirs()

    if not has_allowed_extension(file.filename, SUBTITLE_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Unsupported subtitle format. Use .vtt or .srt")

    ext = get_extension(file.filename)
    base = Path(file.filename).stem
    # Prefix filename with video_id to associate
    dest = build_unique_path(get_subtitle_dir(), base_name=base, ext=ext, prefix=str(video_id))

    await save_upload_file(file, dest, chunk_size=1024 * 256)

    # create sidecar metadata: store language
    meta = {
        "id": _parse_id_from_stem(dest.stem) or 0,
        "video_id": video_id,
        "language": language,
        "file_path": str(dest),
    }
    dest.with_suffix(METADATA_EXT).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    created_at = datetime.fromtimestamp(dest.stat().st_ctime)
    updated_at = datetime.fromtimestamp(dest.stat().st_mtime)

    return SubtitleOut(
        id=meta["id"],
        language=language,
        video_id=video_id,
        file_path=str(dest),
        created_at=created_at,
        updated_at=updated_at,
    )


# PUBLIC_INTERFACE
@router.get(
    "/subtitles/{subtitle_id}/file",
    summary="Get subtitle file",
    description="Return the raw subtitle file contents for a given subtitle ID.",
    responses={404: {"model": ErrorResponse}},
)
async def get_subtitle_file(
    subtitle_id: int = FPath(..., description="Subtitle ID"),
):
    ensure_media_dirs()
    subs_dir = get_subtitle_dir()
    matches = list(subs_dir.glob(f"{subtitle_id}_*.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Subtitle not found")
    path = matches[0]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Subtitle file missing on server")

    media_type = "text/vtt" if path.suffix.lower() == ".vtt" else "text/plain"
    # Include permissive CORS headers so the <track> element can fetch from browser
    resp = FileResponse(path, media_type=media_type, filename=path.name)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Origin, Content-Type, Accept, Range"
    resp.headers["Access-Control-Expose-Headers"] = "Content-Type, Content-Length"
    return resp
