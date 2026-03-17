from __future__ import annotations

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
            "User-Agent": "signfetch",
            "Accept": "text/html, application/linkset+json, text/linkset, */*",
        }
        if headers:
            base_headers.update(headers)

        self._client = client or httpx.Client(
            timeout=timeout,
            follow_redirects=follow_redirects,
            headers=base_headers,
        )

    def head(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        return self._client.head(url, headers=headers)

    def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        return self._client.get(url, headers=headers)

    def open_stream(self, url: str, headers: dict[str, str] | None = None):
        return self._client.stream("GET", url, headers=headers)

    def close(self) -> None:
        if self._owned_client:
            self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()