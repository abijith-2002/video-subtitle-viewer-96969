from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SubtitleBase(BaseModel):
    language: str = Field(..., description="Language code for the subtitle, e.g., en, es, fr")


class SubtitleCreate(SubtitleBase):
    pass


class SubtitleOut(SubtitleBase):
    id: int = Field(..., description="Subtitle unique identifier")
    video_id: int = Field(..., description="Associated video ID")
    file_path: str = Field(..., description="Filesystem path for the subtitle file")
    created_at: datetime
    updated_at: datetime


class VideoBase(BaseModel):
    title: str = Field(..., description="Human readable title for the video")
    description: Optional[str] = Field(None, description="Optional description for the video")


class VideoCreate(VideoBase):
    pass


class VideoOut(VideoBase):
    id: int = Field(..., description="Video unique identifier")
    file_path: str = Field(..., description="Filesystem path for the video file")
    created_at: datetime
    updated_at: datetime
    subtitles: List[SubtitleOut] = Field(default_factory=list, description="List of subtitles linked to this video")
    # Helper client-ready URL to stream the video from this backend
    stream_url: Optional[str] = Field(None, description="Absolute URL to stream this video")


class VideoListItem(BaseModel):
    id: int
    title: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Human friendly error message")
