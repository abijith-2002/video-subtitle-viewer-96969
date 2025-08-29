from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SubtitleBase(BaseModel):
    language: str = Field(..., description="Language code for the subtitle, e.g., en, es, fr")


class SubtitleCreate(SubtitleBase):
    """Placeholder for future validation when creating subtitles."""
    pass


class SubtitleOut(SubtitleBase):
    """Filesystem-based subtitle metadata returned to clients."""
    id: int = Field(..., description="Subtitle identifier derived from filename prefix")
    video_id: int = Field(..., description="Associated video ID (derived from parent video folder/filename)")
    file_path: str = Field(..., description="Filesystem path for the subtitle file")
    created_at: Optional[datetime] = Field(None, description="File creation time (from filesystem if available)")
    updated_at: Optional[datetime] = Field(None, description="Last modification time (from filesystem)")
    file_url: Optional[str] = Field(None, description="Absolute URL to download subtitle file")


class VideoBase(BaseModel):
    title: str = Field(..., description="Human readable title for the video")
    description: Optional[str] = Field(None, description="Optional description for the video")


class VideoCreate(VideoBase):
    """Placeholder for future validation when creating videos."""
    pass


class VideoOut(VideoBase):
    """Filesystem-based video metadata returned to clients."""
    id: int = Field(..., description="Video identifier derived from filename prefix")
    file_path: str = Field(..., description="Filesystem path for the video file")
    created_at: Optional[datetime] = Field(None, description="File creation time (from filesystem if available)")
    updated_at: Optional[datetime] = Field(None, description="Last modification time (from filesystem)")
    subtitles: List[SubtitleOut] = Field(default_factory=list, description="List of subtitles linked to this video")
    stream_url: Optional[str] = Field(None, description="Absolute URL to stream this video")


class VideoListItem(BaseModel):
    id: int
    title: str
    description: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Human friendly error message")
