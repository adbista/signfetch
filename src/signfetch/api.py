from __future__ import annotations

from pathlib import Path

from .downloader import DataDownloader
from .harvester import SignpostingHarvester
from .http_client import HttpClient
from .models import DownloadDataResult


def download_data(
    target: str,
    output_dir: str | Path = 'downloads',
    *,
    timeout: float = 20.0,
) -> DownloadDataResult:
    # Downloads item links discovered via signposting.
    output_path = Path(output_dir)

    with HttpClient(timeout=timeout) as http_client:
        harvester = SignpostingHarvester(http_client)
        resolved_url, item_links = harvester.discover_items(target)
        downloader = DataDownloader(http_client)
        downloaded_items = downloader.download_all(item_links, output_path)

    return DownloadDataResult(
        target=target,
        resolved_url=resolved_url,
        unique_item_count=len(item_links),
        items=downloaded_items,
    )
