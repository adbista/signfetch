from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
import re


_INVALID_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def normalize_url(base_url: str, candidate: str) -> str:
    return urljoin(base_url, candidate.strip())


def filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name

    if name:
        return sanitize_filename(name)

    fallback = parsed.netloc or "downloaded-resource"
    return sanitize_filename(fallback)


def filename_from_url_extension(url: str) -> str | None:
    parsed = urlparse(url)
    name = Path(parsed.path).name

    if not name or not Path(name).suffix:
        return None

    return sanitize_filename(name)


def filename_from_content_disposition(value: str | None) -> str | None:
    if not value:
        return None

    match = re.search(r"filename\*\s*=\s*([^;]+)", value, flags=re.IGNORECASE)
    if match:
        raw = match.group(1).strip().strip('"')
        if "''" in raw:
            raw = raw.split("''", 1)[1]
        return sanitize_filename(unquote(raw))

    match = re.search(r"filename\s*=\s*([^;]+)", value, flags=re.IGNORECASE)
    if match:
        raw = match.group(1).strip().strip('"')
        return sanitize_filename(raw)

    return None


def sanitize_filename(name: str) -> str:
    cleaned = _INVALID_FILENAME_CHARS.sub("_", name).strip("._")
    return cleaned or "downloaded-resource"