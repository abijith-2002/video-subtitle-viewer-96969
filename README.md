# Project Repository

This is the initial README file for the project.

## Backend environment configuration

Create a .env based on the example:

- Navigate to video_subtitles_backend/
- Copy .env.example to .env and adjust values as needed.

Key variables:
- MEDIA_ROOT: Directory where uploaded media is stored (defaults to ./media).
- ENV: Set to development or production.
- SEED_DB: When true in development, seeds the database with a sample record if empty.
- DB_*: PostgreSQL connection settings.

## Regenerate OpenAPI

From video_subtitles_backend/ run:

python -m src.api.generate_openapi

This will update interfaces/openapi.json with the current API schema.