# Video Subtitles Backend

## Introduction

### Overview
The Video Subtitles Backend is a FastAPI service that stores, indexes, and serves video files and their subtitle files using the local filesystem only. It exposes REST endpoints to upload and stream videos, list videos, upload and fetch subtitle files, and check service health. No database is required; metadata is derived from filenames and small JSON sidecar files stored alongside media.

### Scope
This README covers local development and deployment configuration, environment variables, how to run the service, and API usage examples. It also links to the generated OpenAPI specification.

## Getting Started

### Project Structure
- Container root: video_subtitles_backend/
- App entry: src/api/main.py (FastAPI app instance)
- Routers:
  - src/api/routers/videos.py for listing, details, upload, and streaming
  - src/api/routers/subtitles.py for listing subtitles and fetching subtitle files
- Settings: src/api/settings.py (filesystem-only)
- Media storage helpers: src/services/storage.py, src/services/validators.py
- OpenAPI output: interfaces/openapi.json
- Python requirements: requirements.txt

### Prerequisites
- Python 3.11+ recommended
- pip and virtualenv (or your preferred environment manager)

## Key Features

- Upload video files with title and optional description
- Stream video with HTTP range requests (supports browser seeking)
- List available videos and fetch video details (including subtitle links)
- Upload and serve subtitle files (.vtt, .srt, or .ass) - Note: .ass subtitles require special player support
- Health check endpoint
- CORS enabled (wide open by default; tighten in production)

## Environment Variables

Define these variables in your environment or a .env file in video_subtitles_backend/. The service also loads variables via python-dotenv for local dev.

- MEDIA_ROOT: Filesystem path where media is stored. Default: ./media with subfolders videos/ and subtitles/.
- ENV: Environment marker, one of development, production, test. Default: development.

Notes:
- Media directories are created at startup if missing.

## Installation and Local Setup

### 1) Create a virtual environment and install dependencies
- cd video-subtitle-viewer-96969/video_subtitles_backend
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip install -r requirements.txt

### 2) Configure environment variables
Create a .env file in video_subtitles_backend/ (optional):
- MEDIA_ROOT=./media
- ENV=development

### 3) Run the app
With the virtualenv activated, you can start the app in either of the following ways:

- Using Python entrypoint (ensures 'src' is importable):
  python main.py --host 0.0.0.0 --port 8000 --reload

- Using uvicorn directly (works because 'src' is inside the container root):
  uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

## Deployment Guidance

- Ensure MEDIA_ROOT points to a persistent volume. The service writes to:
  - MEDIA_ROOT/videos
  - MEDIA_ROOT/subtitles
- Configure CORS properly. The current app allows all origins. For production, restrict allow_origins in main.py to your frontend origin(s).
- Run behind a reverse proxy or API gateway if needed. The service listens on a configured port (e.g., 8000).

Example container runtime env:
- MEDIA_ROOT=/var/lib/app/media
- ENV=production

## API Endpoints and Usage

Base URL: http://localhost:8000 (or your deployment URL)

- GET /  — Health Check
  Example:
  curl -s http://localhost:8000/

- GET /videos  — List videos (optional ?q=search)
  Example:
  curl -s "http://localhost:8000/videos?q=sample"

- GET /videos/{video_id}  — Get details of a video (includes subtitles and convenience URLs)
  Example:
  curl -s http://localhost:8000/videos/1

- POST /videos/upload  — Upload a new video (multipart/form-data + query)
  Required query: title
  Optional query: description
  Body (multipart): file=<binary video file>
  Example:
  curl -s -X POST "http://localhost:8000/videos/upload?title=My%20Video&description=Demo" \
    -F "file=@/path/to/video.mp4"

- GET /videos/{video_id}/stream  — Stream a video file with HTTP Range support
  Example:
  curl -s -H "Range: bytes=0-1023" http://localhost:8000/videos/1/stream

- GET /videos/{video_id}/subtitles  — List subtitles for a video
  Example:
  curl -s http://localhost:8000/videos/1/subtitles

- POST /videos/{video_id}/subtitles  — Upload a subtitle file for a video
  Path: {video_id}
  Query: ?language=en (or other BCP-47-like code)
  Body (multipart): file=@/path/to/subtitle.vtt
  Example:
  curl -s -X POST "http://localhost:8000/videos/1/subtitles?language=en" \
    -F "file=@/path/to/subtitle.vtt"

- GET /subtitles/{subtitle_id}/file  — Fetch raw subtitle file contents
  Example:
  curl -s http://localhost:8000/subtitles/10/file

## OpenAPI Specification

### Location
- Generated file: video_subtitles_backend/interfaces/openapi.json

### Regenerate OpenAPI
From video_subtitles_backend/ run:
- python -m src.api.generate_openapi

This regenerates the interfaces/openapi.json file using the current application routes.

## Development Notes

- No database is used. Video and subtitle identifiers are derived from filename prefixes (e.g., "12_title.mp4" => id=12).
- Metadata (title, description, language) is persisted in JSON sidecar files next to media files.

## Troubleshooting

- 404 on streaming or subtitle file:
  The file path may be missing on disk. Confirm MEDIA_ROOT is persistent and files exist.
- CORS issues from browser:
  Tighten or adjust CORS settings in src/api/main.py or via deployment proxy.
