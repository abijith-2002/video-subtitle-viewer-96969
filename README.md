# Video Subtitles Backend

## Introduction

### Overview
The Video Subtitles Backend is a FastAPI service that stores, indexes, and serves video files and their subtitle files. It exposes REST endpoints to upload and stream videos, list videos, upload and fetch subtitle files, and check service health. Data is persisted in PostgreSQL using SQLAlchemy (async), while binary media is stored on disk under a configurable media root.

### Scope
This README covers local development and deployment configuration, environment variables, how to run the service, startup order with the frontend, and API usage examples. It also links to the generated OpenAPI specification.

## Getting Started

### Project Structure
- Container root: video_subtitles_backend/
- App entry: src/api/main.py (FastAPI app instance)
- Routers:
  - src/api/routers/videos.py for listing, details, upload, and streaming
  - src/api/routers/subtitles.py for listing subtitles and fetching subtitle files
- Settings: src/api/settings.py
- Database: src/db/models.py, src/db/session.py, src/db/seed.py
- Media storage helpers: src/services/storage.py, src/services/validators.py
- OpenAPI output: interfaces/openapi.json
- Python requirements: requirements.txt

### Prerequisites
- Python 3.11+ recommended
- PostgreSQL instance accessible from the backend container/environment
- pip and virtualenv (or your preferred environment manager)

## Key Features

- Upload video files with title and optional description
- Stream video with HTTP range requests (supports browser seeking)
- List available videos and fetch video details (including subtitle links)
- Upload subtitle files (.vtt or .srt) and retrieve raw subtitle files
- Health check endpoint
- CORS enabled (wide open by default; tighten in production)

## Environment Variables

Define these variables in your environment or a .env file in video_subtitles_backend/. The service also loads variables via python-dotenv for local dev.

- MEDIA_ROOT: Filesystem path where media is stored. Default: ./media with subfolders videos/ and subtitles/.
- ENV: Environment marker, one of development, production, test. Default: development.
- SEED_DB: When true/1/yes in development, seeds the DB with a sample video record if empty on startup. Default: false.
- DB_HOST: PostgreSQL host. Required.
- DB_PORT: PostgreSQL port. Required.
- DB_NAME: Database name. Required.
- DB_USER: Database user. Required.
- DB_PASSWORD: Database password. Required.

Notes:
- Database DSN is built in src/db/session.py and raises an error if any DB_* variable is missing.
- Media directories are created at startup if missing.

## Installation and Local Setup

### 1) Create a virtual environment and install dependencies
- cd video-subtitle-viewer-96969/video_subtitles_backend
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip install -r requirements.txt

### 2) Configure environment variables
Create a .env file in video_subtitles_backend/ with at least:
- DB_HOST=localhost
- DB_PORT=5432
- DB_NAME=video_subtitles
- DB_USER=postgres
- DB_PASSWORD=postgres
- MEDIA_ROOT=./media
- ENV=development
- SEED_DB=true

Ensure the PostgreSQL database exists and is reachable.

### 3) Run the app
With the virtualenv activated, you can start the app in either of the following ways:

- Using Python entrypoint (ensures 'src' is importable):
  python main.py --host 0.0.0.0 --port 8000 --reload

- Using uvicorn directly (works because 'src' is inside the container root):
  uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

On first run, tables are created automatically and, if ENV=development and SEED_DB=true, a sample placeholder video entry is seeded.

## Deployment Guidance

- Provide all DB_* variables through your platform’s secret/var management (do not bake secrets into images).
- Set ENV=production and typically SEED_DB=false.
- Ensure MEDIA_ROOT points to a persistent volume. The service writes to:
  - MEDIA_ROOT/videos
  - MEDIA_ROOT/subtitles
- Configure CORS properly. The current app allows all origins. For production, restrict allow_origins in main.py to your frontend origin(s).
- Run behind a reverse proxy or API gateway if needed. The service listens on a configured port (e.g., 8000).

Example container runtime env:
- DB_HOST=postgres
- DB_PORT=5432
- DB_NAME=video_subtitles
- DB_USER=app
- DB_PASSWORD=secret
- MEDIA_ROOT=/var/lib/app/media
- ENV=production
- SEED_DB=false

## Startup Order

- Start PostgreSQL first and ensure readiness.
- Start the backend service (this service) and confirm the health endpoint is healthy.
- Start the frontend after the backend is reachable, and point the frontend to the backend URL.

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
  Language parameter: currently passed as a path parameter in code signature but better supplied as query. Clients in this repo send it as ?language=en.
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

- The database is initialized on startup (simple table creation). For production-grade schema evolution, adopt Alembic migrations.
- CORS is permissive by default to ease local dev. Restrict it for production.
- The seeding utility creates a placeholder file when no sample is provided; replace it with a real sample asset for demos if desired.

## Troubleshooting

- Error: Missing required database env vars: ...
  Ensure all DB_* variables are provided and correct.
- 404 on streaming or subtitle file:
  The file path may be missing on disk. Confirm MEDIA_ROOT is persistent and files exist.
- CORS issues from browser:
  Tighten or adjust CORS settings in src/api/main.py or via deployment proxy.