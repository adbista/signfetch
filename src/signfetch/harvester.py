from __future__ import annotations

from collections import OrderedDict

from .http_client import HttpClient
from .models import SignpostLink
from .parsers import HtmlLinkParser, LinkHeaderParser, LinksetParser


class SignpostingHarvester:
    def __init__(self, http_client: HttpClient) -> None:
        self._http = http_client
        self._link_header_parser = LinkHeaderParser()
        self._html_parser = HtmlLinkParser()
        self._linkset_parser = LinksetParser()

    def discover_items(self, target: str) -> tuple[str, list[SignpostLink]]:
        discovered: list[SignpostLink] = []

        head_response = self._http.head(target)
        head_response.raise_for_status()
        resolved_url = str(head_response.url)

        discovered.extend(
            self._parse_link_headers(
                head_response.headers.get_list("link"),
                resolved_url,
                source="http-header",
            )
        )

        get_response = self._http.get(resolved_url)
        get_response.raise_for_status()

        discovered.extend(
            self._parse_link_headers(
                get_response.headers.get_list("link"),
                str(get_response.url),
                source="http-header",
            )
        )
        discovered.extend(
            self._html_parser.parse(
                get_response.text,
                str(get_response.url),
                source="html-link",
            )
        )

        linksets = [link for link in discovered if link.rel == "linkset"]
        for linkset in linksets:
            linkset_response = self._http.get(linkset.url)
            linkset_response.raise_for_status()

            discovered.extend(
                self._linkset_parser.parse(
                    linkset_response.text,
                    base_url=str(linkset_response.url),
                    source="linkset",
                    content_type=linkset_response.headers.get("content-type"),
                )
            )

        item_links = [link for link in discovered if link.rel == "item"]
        unique_items = self._deduplicate(item_links)

        return str(get_response.url), unique_items

    def _parse_link_headers(self, values: list[str], base_url: str, source: str) -> list[SignpostLink]:
        return self._link_header_parser.parse(values, base_url=base_url, source=source)

    def _deduplicate(self, links: list[SignpostLink]) -> list[SignpostLink]:
        unique: OrderedDict[str, SignpostLink] = OrderedDict()
        for link in links:
            unique.setdefault(link.url, link)
        return list(unique.values())