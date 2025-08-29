#!/usr/bin/env python3
"""
Entrypoint to run the FastAPI application.

This script ensures that the 'src' directory is discoverable as a package/module
when running the app via `python main.py`, and starts a uvicorn server.

Usage:
    - python main.py                      # starts uvicorn with defaults (0.0.0.0:8000, reload if dev)
    - python main.py --host 0.0.0.0 --port 8000 --reload

Environment variables required by the app (database, etc.) should be provided
in the environment or via a .env file located in the container root.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """
    Ensure that the project root (containing the 'src' package) is on sys.path.

    When executing `python main.py` from the container root, Python may not
    include the current directory on sys.path in some environments. We defensively
    add the container root so `import src...` works consistently.
    """
    container_root = Path(__file__).resolve().parent
    # In this project, 'src' lives directly under container_root
    if str(container_root) not in sys.path:
        sys.path.insert(0, str(container_root))


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for uvicorn."""
    parser = argparse.ArgumentParser(description="Run Video Subtitles Backend (FastAPI)")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Host to bind")
    parser.add_argument("--port", default=int(os.getenv("PORT", "8000")), type=int, help="Port to bind")
    # Enable reload automatically for development environments
    default_reload = os.getenv("ENV", "development").lower() in {"dev", "development"}
    parser.add_argument("--reload", action="store_true", default=default_reload, help="Enable auto-reload (dev)")
    return parser.parse_args()


def main() -> None:
    """Main entry to launch uvicorn for src.api.main:app."""
    _ensure_src_on_path()

    # Import after path setup
    try:
        import uvicorn  # type: ignore
    except Exception:
        # Provide a helpful message if uvicorn is missing
        print("ERROR: uvicorn is not installed. Please install dependencies with `pip install -r requirements.txt`.", file=sys.stderr)
        raise

    args = parse_args()
    # Launch uvicorn referencing the app inside the 'src' package
    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=False,
    )


if __name__ == "__main__":
    main()
