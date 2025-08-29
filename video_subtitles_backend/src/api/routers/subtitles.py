from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Path as FPath, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse, SubtitleOut
from src.db.models import Subtitle, Video
from src.db.session import get_async_session

router = APIRouter(prefix="", tags=["Subtitles"])

MEDIA_BASE = Path("media")
SUB_DIR = MEDIA_BASE / "subtitles"


def _ext_is_subtitle(ext: str) -> bool:
    return ext.lower() in {".vtt", ".srt"}


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
    session: AsyncSession = Depends(get_async_session),
):
    v = await session.get(Video, video_id)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")

    stmt = select(Subtitle).where(Subtitle.video_id == video_id).order_by(Subtitle.created_at.asc())
    res = await session.execute(stmt)
    subs = []
    for s in res.scalars().all():
        subs.append(
            SubtitleOut(
                id=s.id,
                language=s.language,
                video_id=s.video_id,
                file_path=s.file_path,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )
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
    language: str = FPath(..., description="Language code (e.g. en, es, fr) in URL path is not ideal; pass as query or use form-data in future"),
    file: UploadFile = File(..., description="Subtitle file (.vtt or .srt)"),
    session: AsyncSession = Depends(get_async_session),
):
    v = await session.get(Video, video_id)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded subtitle must have a filename")

    SUB_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix
    if not _ext_is_subtitle(ext):
        raise HTTPException(status_code=400, detail="Unsupported subtitle format. Use .vtt or .srt")

    base = Path(file.filename).stem
    dest = SUB_DIR / f"{video_id}_{base}{ext}"
    counter = 1
    while dest.exists():
        dest = SUB_DIR / f"{video_id}_{base}_{counter}{ext}"
        counter += 1

    try:
        with dest.open("wb") as out:
            while chunk := await file.read(1024 * 256):
                out.write(chunk)
    finally:
        await file.close()

    s = Subtitle(language=language, video_id=video_id, file_path=str(dest))
    session.add(s)
    await session.flush()

    return SubtitleOut(
        id=s.id,
        language=s.language,
        video_id=s.video_id,
        file_path=s.file_path,
        created_at=s.created_at,
        updated_at=s.updated_at,
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
    session: AsyncSession = Depends(get_async_session),
):
    s = await session.get(Subtitle, subtitle_id)
    if not s:
        raise HTTPException(status_code=404, detail="Subtitle not found")
    path = Path(s.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Subtitle file missing on server")

    media_type = "text/vtt" if path.suffix.lower() == ".vtt" else "text/plain"
    return FileResponse(path, media_type=media_type)
