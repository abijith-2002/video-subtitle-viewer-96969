from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


# Accepted extensions
# Include a broader set of common web-playable formats so manual files are detected.
VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".ogg", ".ogv",
}
SUBTITLE_EXTENSIONS = {
    ".vtt", ".srt",  # Note: .ass/.ssa are not served as text/vtt; keep common ones
}

# Very basic BCP-47-ish checker (allows en, en-US, pt-BR, zh-Hans, etc.)
LANG_CODE_REGEX = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


# PUBLIC_INTERFACE
def has_allowed_extension(filename: str, allowed: Iterable[str]) -> bool:
    """Check if a filename has an allowed extension.

    Args:
        filename: The filename to check.
        allowed: An iterable of extensions (with leading dot), case-insensitive.

    Returns:
        True if the filename's extension is in the allowed set.
    """
    ext = Path(filename).suffix.lower()
    return ext in {e.lower() for e in allowed}


# PUBLIC_INTERFACE
def is_valid_language_code(code: str) -> bool:
    """Validate a language code using a permissive regex for BCP-47 style tags.

    Examples accepted:
        en, es, fr, en-US, pt-BR, zh-Hans

    Args:
        code: Language code to validate.

    Returns:
        True if code is syntactically valid.
    """
    if not code:
        return False
    return bool(LANG_CODE_REGEX.fullmatch(code))


# PUBLIC_INTERFACE
def get_extension(filename: str) -> str:
    """Return the lowercase extension of a filename (including dot)."""
    return Path(filename).suffix.lower()
