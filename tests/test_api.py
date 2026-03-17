import httpx
import respx

from signfetch import list_item_links


@respx.mock
def test_list_item_links_returns_only_item_links_with_optional_type() -> None:
    landing = "https://example.org/record"
    linkset = "https://example.org/linkset.json"
    data_with_type = "https://example.org/files/a.csv"
    data_without_type = "https://example.org/files/b"

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={"Link": f'<{linkset}>; rel="linkset"; type="application/linkset+json"'},
            request=httpx.Request("HEAD", landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(
            200,
            headers={
                "Content-Type": "text/html",
                "Link": f'<{data_with_type}>; rel="item"; type="text/csv", <https://example.org/meta>; rel="describedby"',
            },
            text=f'<html><head><link rel="item" href="{data_without_type}"></head></html>',
            request=httpx.Request("GET", landing),
        )
    )
    respx.get(linkset).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/linkset+json"},
            json={
                "linkset": [
                    {
                        "item": [
                            {"href": data_with_type, "type": "text/csv"},
                            {"href": data_without_type},
                        ]
                    }
                ]
            },
            request=httpx.Request("GET", linkset),
        )
    )

    links = list_item_links(landing)

    assert [link.url for link in links] == [data_with_type, data_without_type]
    assert [link.type for link in links] == ["text/csv", None]


@respx.mock
def test_list_item_links_returns_empty_when_no_items() -> None:
    landing = "https://example.org/record"

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            request=httpx.Request("HEAD", landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            text="<html><head></head><body>no items</body></html>",
            request=httpx.Request("GET", landing),
        )
    )

    links = list_item_links(landing)

    assert links == []
