from __future__ import annotations

from typing import Iterable

import httpx


class HttpClient:
    def __init__(
        self,
        timeout: float = 20.0,
        follow_redirects: bool = True,
        headers: dict[str, str] | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._owned_client = client is None
        base_headers = {
            "User-Agent": "signfetch/0.1.0",
            "Accept": "text/html, application/linkset+json, text/linkset, */*",
        }
        if headers:
            base_headers.update(headers)
        self._client = client or httpx.Client(
            timeout=timeout,
            follow_redirects=follow_redirects,
            headers=base_headers,
        )

    def head(self, url: str) -> httpx.Response:
        return self._client.head(url)

    def get(self, url: str) -> httpx.Response:
        return self._client.get(url)

    def stream_download(self, url: str) -> Iterable[bytes]:
        with self._client.stream("GET", url) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                if chunk:
                    yield chunk

    def open_stream(self, url: str) -> httpx.Response:
        return self._client.stream("GET", url)

    def close(self) -> None:
        if self._owned_client:
            self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
