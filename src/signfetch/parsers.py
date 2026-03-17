from __future__ import annotations

from email.utils import unquote
import json

from bs4 import BeautifulSoup

from .models import SignpostLink
from .utils import normalize_url


def _make_signpost_link(
    href: str,
    rel: str,
    base_url: str,
    source: str,
    *,
    type: str | None = None,
    profile: str | None = None,
) -> SignpostLink:
    return SignpostLink(
        url=normalize_url(base_url, href),
        rel=rel,
        type=type,
        profile=profile,
        source=source,
    )


class LinkHeaderParser:
    def parse(self, raw_value: str | list[str] | None, base_url: str, source: str) -> list[SignpostLink]:
        if not raw_value:
            return []

        header_values = [raw_value] if isinstance(raw_value, str) else raw_value
        links: list[SignpostLink] = []

        for header in header_values:
            for part in self._split_link_value(header):
                parsed = self._parse_part(part, base_url, source)
                if parsed is not None:
                    links.append(parsed)

        return links

    def _split_link_value(self, value: str) -> list[str]:
        parts: list[str] = []
        current: list[str] = []
        in_quotes = False

        for char in value:
            if char == '"':
                in_quotes = not in_quotes

            if char == "," and not in_quotes:
                part = "".join(current).strip()
                if part:
                    parts.append(part)
                current = []
                continue

            current.append(char)

        final = "".join(current).strip()
        if final:
            parts.append(final)

        return parts

    def _parse_part(self, part: str, base_url: str, source: str) -> SignpostLink | None:
        if not part.startswith("<") or ">" not in part:
            return None

        href, rest = part[1:].split(">", 1)
        params: dict[str, str] = {}

        for raw_param in rest.split(";"):
            raw_param = raw_param.strip()
            if not raw_param or "=" not in raw_param:
                continue

            key, value = raw_param.split("=", 1)
            params[key.strip().lower()] = unquote(value.strip().strip('"'))

        rel = params.get("rel")
        if not rel:
            return None

        return _make_signpost_link(
            href=href,
            rel=rel,
            base_url=base_url,
            source=source,
            type=params.get("type"),
            profile=params.get("profile"),
        )


class HtmlLinkParser:
    def parse(self, html: str, base_url: str, source: str) -> list[SignpostLink]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[SignpostLink] = []

        for element in soup.find_all("link", href=True):
            rel_values = element.get("rel") or []
            if isinstance(rel_values, str):
                rel_values = [rel_values]

            for rel in rel_values:
                links.append(
                    _make_signpost_link(
                        href=element["href"],
                        rel=str(rel),
                        base_url=base_url,
                        source=source,
                        type=element.get("type"),
                        profile=element.get("profile"),
                    )
                )

        return links


class LinksetParser:
    def __init__(self) -> None:
        self._header_parser = LinkHeaderParser()

    def parse(
        self,
        content: str,
        base_url: str,
        source: str,
        content_type: str | None = None,
    ) -> list[SignpostLink]:
        if content_type and "application/linkset+json" in content_type:
            return self._parse_json(content, base_url, source)

        if content.lstrip().startswith("{"):
            return self._parse_json(content, base_url, source)

        return self._header_parser.parse(content, base_url=base_url, source=source)

    def _parse_json(self, content: str, base_url: str, source: str) -> list[SignpostLink]:
        data = json.loads(content)
        links: list[SignpostLink] = []

        items = data.get("linkset", data)
        if isinstance(items, dict):
            items = [items]

        if not isinstance(items, list):
            return links

        for entry in items:
            if not isinstance(entry, dict):
                continue

            for rel, rel_value in entry.items():
                if rel in {"anchor", "context"}:
                    continue

                if isinstance(rel_value, dict):
                    rel_value = [rel_value]

                if not isinstance(rel_value, list):
                    continue

                for obj in rel_value:
                    if not isinstance(obj, dict) or "href" not in obj:
                        continue

                    links.append(
                        _make_signpost_link(
                            href=obj["href"],
                            rel=rel,
                            base_url=base_url,
                            source=source,
                            type=obj.get("type"),
                            profile=obj.get("profile"),
                        )
                    )

        return links