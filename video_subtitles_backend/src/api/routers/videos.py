from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path as FPath, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse, VideoListItem, VideoOut
from src.db.models import Video
from src.db.session import get_async_session
from src.services.storage import ensure_media_dirs, get_video_dir, build_unique_path, save_upload_file
from src.services.validators import VIDEO_EXTENSIONS, has_allowed_extension, get_extension

router = APIRouter(prefix="/videos", tags=["Videos"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[VideoListItem],
    summary="List videos",
    description="Returns a list of available videos without heavy fields.",
    responses={404: {"model": ErrorResponse}},
)
async def list_videos(
    session: AsyncSession = Depends(get_async_session),
    q: Optional[str] = Query(default=None, description="Optional search string to filter by title"),
):
    """List all videos optionally filtered by a search query."""
    stmt = select(Video)
    if q:
        # simple ilike filter
        stmt = stmt.where(Video.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Video.created_at.desc())
    res = await session.execute(stmt)
    items = []
    for v in res.scalars().all():
        items.append(
            VideoListItem(
                id=v.id,
                title=v.title,
                description=v.description,
                created_at=v.created_at,
                updated_at=v.updated_at,
            )
        )
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
async def get_video(
    video_id: int = FPath(..., description="ID of the video"),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a single video by ID including its subtitles."""
    obj = await session.get(Video, video_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Video not found")

    # Load subtitles
    await session.refresh(obj)
    subs = []
    for s in obj.subtitles:
        subs.append(
            {
                "id": s.id,
                "language": s.language,
                "video_id": s.video_id,
                "file_path": s.file_path,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
        )

    return VideoOut(
        id=obj.id,
        title=obj.title,
        description=obj.description,
        file_path=obj.file_path,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        subtitles=subs,
    )


# PUBLIC_INTERFACE
@router.post(
    "/upload",
    response_model=VideoOut,
    summary="Upload a new video",
    description="Upload a video file and create a database record with its metadata.",
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def upload_video(
    title: str = Query(..., description="Title for the uploaded video"),
    description: Optional[str] = Query(default=None, description="Optional description"),
    file: UploadFile = File(..., description="Binary video file to upload"),
    session: AsyncSession = Depends(get_async_session),
):
    """Upload a video file and persist metadata in the database."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

    ensure_media_dirs()

    if not has_allowed_extension(file.filename, VIDEO_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Unsupported video format")

    ext = get_extension(file.filename)
    base_name = Path(file.filename).stem
    dest_path = build_unique_path(get_video_dir(), base_name=base_name, ext=ext)

    # Save file to disk
    await save_upload_file(file, dest_path)

    # Create DB record
    v = Video(title=title, description=description, file_path=str(dest_path))
    session.add(v)
    await session.flush()  # obtain ID

    # Prepare response
    return await get_video(video_id=v.id, session=session)  # reuse detail builder


# PUBLIC_INTERFACE
@router.get(
    "/{video_id}/stream",
    summary="Stream video content",
    description="Stream the binary contents of a video file by ID.",
    responses={404: {"model": ErrorResponse}},
)
async def stream_video(
    video_id: int = FPath(..., description="ID of the video to stream"),
    session: AsyncSession = Depends(get_async_session),
):
    """Return a streaming response for the video file."""
    v = await session.get(Video, video_id)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    path = Path(v.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file missing on server")

    # Let Starlette handle efficient file response; browsers can stream/progress
    # For full HTTP range support, a custom range streamer could be added later.
    return FileResponse(path, media_type="video/mp4")
