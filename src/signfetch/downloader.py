from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import zipfile

from .http_client import HttpClient
from .models import DownloadedItem, SignpostLink
from .utils import (
    extension_from_content_type,
    filename_from_content_disposition,
    filename_from_url,
    filename_from_url_extension,
    sanitize_filename,
)


class DataDownloader:
    def __init__(self, http_client: HttpClient) -> None:
        self._http = http_client

    def download_all(self, items: list[SignpostLink], output_dir: Path) -> list[DownloadedItem]:
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded: list[DownloadedItem] = []
        used_names: set[str] = set()

        for item in items:
            with self._http.open_stream(item.url) as response:
                response.raise_for_status()
                filename, packaged = self._resolve_filename(item.url, response.headers, used_names)
                if packaged:
                    temp_path = output_dir / f".tmp_{uuid4().hex}"
                    with temp_path.open('wb') as handle:
                        for chunk in response.iter_bytes():
                            if chunk:
                                handle.write(chunk)
                    destination = output_dir / filename
                    try:
                        self._write_zip(temp_path, destination)
                    finally:
                        temp_path.unlink(missing_ok=True)
                    media_type = 'application/zip'
                else:
                    destination = output_dir / filename
                    with destination.open('wb') as handle:
                        for chunk in response.iter_bytes():
                            if chunk:
                                handle.write(chunk)
                    media_type = self._detect_media_type(response.headers.get('content-type'), item.url)

                downloaded.append(
                    DownloadedItem(
                        url=item.url,
                        saved_path=destination,
                        source=item.source,
                        media_type=media_type,
                        filename=filename,
                    )
                )
        return downloaded

    def _unique_filename(self, filename: str, used_names: set[str]) -> str:
        if filename not in used_names:
            used_names.add(filename)
            return filename
        stem, dot, suffix = filename.partition('.')
        counter = 2
        while True:
            candidate = f"{stem}_{counter}{dot}{suffix}" if dot else f"{stem}_{counter}"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
            counter += 1

    def _resolve_filename(self, url: str, headers: dict[str, str], used_names: set[str]) -> tuple[str, bool]:
        content_name = filename_from_content_disposition(headers.get('content-disposition'))
        if content_name:
            return self._unique_filename(content_name, used_names), False

        url_name = filename_from_url_extension(url)
        if url_name:
            return self._unique_filename(url_name, used_names), False

        extension = extension_from_content_type(headers.get('content-type'))
        if extension:
            base = filename_from_url(url)
            base_stem = Path(base).stem
            name = sanitize_filename(f"{base_stem}{extension}")
            return self._unique_filename(name, used_names), False

        base = filename_from_url(url)
        base_stem = Path(base).stem
        name = sanitize_filename(f"{base_stem}.zip")
        return self._unique_filename(name, used_names), True

    def _detect_media_type(self, content_type: str | None, url: str) -> str | None:
        if content_type:
            return content_type.split(';', 1)[0].strip().lower()
        lowered = url.lower()
        if lowered.endswith('.csv'):
            return 'text/csv'
        if lowered.endswith('.json'):
            return 'application/json'
        if lowered.endswith('.zip'):
            return 'application/zip'
        return None

    def _write_zip(self, source: Path, destination: Path) -> None:
        with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as zip_handle:
            zip_handle.write(source, arcname='payload')
