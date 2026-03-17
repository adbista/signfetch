from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
import zipfile

from .http_client import HttpClient
from .models import DownloadedItem, SignpostLink
from .utils import (
    filename_from_content_disposition,
    filename_from_url,
    filename_from_url_extension,
    sanitize_filename,
)


class DataDownloader:
    def __init__(self, http_client: HttpClient) -> None:
        self._http = http_client

    def download_all(
        self,
        items: list[SignpostLink],
        output_dir: Path,
        referer: str | None = None,
        max_workers: int = 4,
    ) -> list[DownloadedItem]:
        output_dir.mkdir(parents=True, exist_ok=True)
        request_headers = self._build_download_headers(referer)
        worker_count = max(1, min(max_workers, len(items) or 1))

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            buffered = list(executor.map(lambda item: self._fetch_item(item, request_headers), items))

        used_names: set[str] = set()
        downloaded: list[DownloadedItem] = []

        for item, final_url, headers, content in buffered:
            filename, packaged = self._resolve_filename(final_url, headers, used_names)
            destination = output_dir / filename

            if packaged:
                temp_path = output_dir / f".tmp_{uuid4().hex}"
                try:
                    temp_path.write_bytes(content)
                    self._write_zip(temp_path, destination)
                finally:
                    temp_path.unlink(missing_ok=True)
            else:
                destination.write_bytes(content)

            downloaded.append(
                DownloadedItem(
                    url=item.url,
                    saved_path=destination,
                    source=item.source,
                    filename=filename,
                )
            )

        return downloaded

    def _fetch_item(
        self,
        item: SignpostLink,
        request_headers: dict[str, str],
    ) -> tuple[SignpostLink, str, dict[str, str], bytes]:
        with self._http.open_stream(item.url, headers=request_headers) as response:
            response.raise_for_status()
            final_url = str(response.url)
            headers = dict(response.headers)
            content = b"".join(chunk for chunk in response.iter_bytes() if chunk)
        return item, final_url, headers, content

    def _build_download_headers(self, referer: str | None) -> dict[str, str]:
        headers = {"Accept": "*/*"}

        if not referer:
            return headers

        headers["Referer"] = referer

        parts = urlsplit(referer)
        if parts.scheme and parts.netloc:
            headers["Origin"] = f"{parts.scheme}://{parts.netloc}"

        return headers

    def _unique_filename(self, filename: str, used_names: set[str]) -> str:
        if filename not in used_names:
            used_names.add(filename)
            return filename

        path = Path(filename)
        stem = path.stem
        suffix = path.suffix
        counter = 2

        while True:
            candidate = f"{stem}_{counter}{suffix}"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
            counter += 1

    def _resolve_filename(
        self,
        url: str,
        headers,
        used_names: set[str],
    ) -> tuple[str, bool]:
        content_name = filename_from_content_disposition(headers.get("content-disposition"))
        if content_name:
            return self._unique_filename(content_name, used_names), False

        url_name = filename_from_url_extension(url)
        if url_name:
            return self._unique_filename(url_name, used_names), False

        base = filename_from_url(url)
        base_stem = Path(base).stem
        fallback_name = sanitize_filename(f"{base_stem}.zip")
        return self._unique_filename(fallback_name, used_names), True

    def _write_zip(self, source: Path, destination: Path) -> None:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
            zip_handle.write(source, arcname="payload")