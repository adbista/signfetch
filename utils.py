from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
import re

_INVALID_FILENAME_CHARS = re.compile(r'[^A-Za-z0-9._-]+')
_CONTENT_TYPE_EXTENSIONS = {
    'text/csv': '.csv',
    'text/plain': '.txt',
    'text/html': '.html',
    'text/markdown': '.md',
    'text/xml': '.xml',
    'application/xml': '.xml',
    'application/json': '.json',
    'application/ld+json': '.jsonld',
    'application/geo+json': '.geojson',
    'application/zip': '.zip',
    'application/x-zip-compressed': '.zip',
    'application/gzip': '.gz',
    'application/x-gzip': '.gz',
    'application/x-tar': '.tar',
    'application/tar': '.tar',
    'application/x-7z-compressed': '.7z',
    'application/x-bzip2': '.bz2',
    'application/x-rar-compressed': '.rar',
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.ms-excel': '.xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/vnd.ms-powerpoint': '.ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/tiff': '.tif',
    'image/gif': '.gif',
    'image/svg+xml': '.svg',
}


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


def extension_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    media_type = content_type.split(';', 1)[0].strip().lower()
    extension = _CONTENT_TYPE_EXTENSIONS.get(media_type)
    if extension:
        return extension
    if '+' in media_type:
        suffix = media_type.split('+', 1)[1]
        return _CONTENT_TYPE_EXTENSIONS.get(f"application/{suffix}")
    return None



def sanitize_filename(name: str) -> str:
    cleaned = _INVALID_FILENAME_CHARS.sub("_", name).strip("._")
    return cleaned or "downloaded-resource"
