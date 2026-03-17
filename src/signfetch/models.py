from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SignpostLink:
    url: str
    rel: str
    type: str | None = None
    profile: str | None = None
    source: str = "unknown"


@dataclass(frozen=True)
class DownloadedItem:
    url: str
    saved_path: Path
    source: str
    media_type: str | None = None
    filename: str | None = None


@dataclass(frozen=True)
class DownloadDataResult:
    target: str
    resolved_url: str
    unique_item_count: int
    items: list[DownloadedItem] = field(default_factory=list)
