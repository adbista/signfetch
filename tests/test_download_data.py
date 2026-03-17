from pathlib import Path
import zipfile

import httpx
import respx

from signfetch import download_data


@respx.mock
def test_download_data_harvests_http_html_and_linkset_items_and_deduplicates(tmp_path: Path) -> None:
    landing = "https://example.org/record"
    linkset = "https://example.org/linkset.json"
    data_a = "https://example.org/files/a.csv"
    data_b = "https://example.org/files/b.csv"
    data_c = "https://example.org/files/c.zip"

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={
                "Link": f'<{data_a}>; rel="item"; type="text/csv", <{linkset}>; rel="linkset"; type="application/linkset+json"'
            },
            request=httpx.Request("HEAD", landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(
            200,
            headers={
                "Content-Type": "text/html",
                "Link": f'<{data_a}>; rel="item"; type="text/csv"',
            },
            text=f"""
                <html><head>
                <link rel="item" href="{data_b}" type="text/csv">
                <link rel="linkset" href="{linkset}" type="application/linkset+json">
                </head><body>record</body></html>
            """,
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
                            {"href": data_c, "type": "application/zip"},
                            {"href": data_b, "type": "text/csv"},
                        ]
                    }
                ]
            },
            request=httpx.Request("GET", linkset),
        )
    )
    respx.get(data_a).mock(
        return_value=httpx.Response(200, content=b"alpha", request=httpx.Request("GET", data_a))
    )
    respx.get(data_b).mock(
        return_value=httpx.Response(200, content=b"beta", request=httpx.Request("GET", data_b))
    )
    respx.get(data_c).mock(
        return_value=httpx.Response(200, content=b"gamma", request=httpx.Request("GET", data_c))
    )

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 3
    assert [item.url for item in result.items] == [data_a, data_b, data_c]
    assert (tmp_path / "a.csv").read_bytes() == b"alpha"
    assert (tmp_path / "b.csv").read_bytes() == b"beta"
    assert (tmp_path / "c.zip").read_bytes() == b"gamma"


@respx.mock
def test_download_data_returns_empty_when_no_item_signposting(tmp_path: Path) -> None:
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
            text="<html><head></head><body>no signposting items</body></html>",
            request=httpx.Request("GET", landing),
        )
    )

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 0
    assert result.items == []
    assert result.resolved_url == landing
    assert list(tmp_path.iterdir()) == []


@respx.mock
def test_download_data_uses_unique_filenames_when_url_paths_collide(tmp_path: Path) -> None:
    landing = "https://example.org/record"
    data_a = "https://example.org/files/report"
    data_b = "https://example.org/other/report"

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={"Link": f'<{data_a}>; rel="item", <{data_b}>; rel="item"'},
            request=httpx.Request("HEAD", landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(200, text="<html></html>", request=httpx.Request("GET", landing))
    )
    respx.get(data_a).mock(
        return_value=httpx.Response(
            200,
            content=b"one",
            request=httpx.Request("GET", data_a),
        )
    )
    respx.get(data_b).mock(
        return_value=httpx.Response(
            200,
            content=b"two",
            request=httpx.Request("GET", data_b),
        )
    )

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 2

    archive_1 = tmp_path / "report.zip"
    archive_2 = tmp_path / "report_2.zip"

    assert archive_1.exists()
    assert archive_2.exists()

    with zipfile.ZipFile(archive_1, "r") as archive:
        assert archive.namelist() == ["payload"]
        assert archive.read("payload") == b"one"

    with zipfile.ZipFile(archive_2, "r") as archive:
        assert archive.namelist() == ["payload"]
        assert archive.read("payload") == b"two"


@respx.mock
def test_download_data_prefers_content_disposition_filename(tmp_path: Path) -> None:
    landing = "https://example.org/record"
    data_url = "https://example.org/files/download"

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={"Link": f'<{data_url}>; rel="item"'},
            request=httpx.Request("HEAD", landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(200, text="<html></html>", request=httpx.Request("GET", landing))
    )
    respx.get(data_url).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Disposition": 'attachment; filename="real.csv"'},
            content=b"alpha",
            request=httpx.Request("GET", data_url),
        )
    )

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 1
    assert (tmp_path / "real.csv").read_bytes() == b"alpha"


@respx.mock
def test_download_data_uses_url_extension_when_no_content_disposition(tmp_path: Path) -> None:
    landing = "https://example.org/record"
    data_url = "https://example.org/files/report.json"

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={"Link": f'<{data_url}>; rel="item"'},
            request=httpx.Request("HEAD", landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(200, text="<html></html>", request=httpx.Request("GET", landing))
    )
    respx.get(data_url).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "text/plain"},
            content=b"{}",
            request=httpx.Request("GET", data_url),
        )
    )

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 1
    assert (tmp_path / "report.json").read_bytes() == b"{}"


@respx.mock
def test_download_data_packages_to_zip_when_no_hints(tmp_path: Path) -> None:
    landing = "https://example.org/record"
    data_url = "https://example.org/files/opaque"

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={"Link": f'<{data_url}>; rel="item"'},
            request=httpx.Request("HEAD", landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(200, text="<html></html>", request=httpx.Request("GET", landing))
    )
    respx.get(data_url).mock(
        return_value=httpx.Response(
            200,
            headers={},
            content=b"payload",
            request=httpx.Request("GET", data_url),
        )
    )

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 1
    archive_path = tmp_path / "opaque.zip"
    assert archive_path.exists()

    with zipfile.ZipFile(archive_path, "r") as archive:
        assert archive.namelist() == ["payload"]
        assert archive.read("payload") == b"payload"


@respx.mock
def test_download_data_sends_referer_when_downloading_items(tmp_path: Path) -> None:
    landing = "https://example.org/record"
    data_url = "https://example.org/files/a.csv"

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={"Link": f'<{data_url}>; rel="item"'},
            request=httpx.Request("HEAD", landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(
            200,
            text="<html></html>",
            request=httpx.Request("GET", landing),
        )
    )

    def item_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Referer") == landing
        assert request.headers.get("Origin") == "https://example.org"
        return httpx.Response(200, content=b"alpha", request=request)

    respx.get(data_url).mock(side_effect=item_handler)

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 1
    assert (tmp_path / "a.csv").read_bytes() == b"alpha"


@respx.mock
def test_download_data_uses_final_redirect_url_for_filename(tmp_path: Path) -> None:
    landing = "https://example.org/record"
    data_url = "https://example.org/files/download"
    final_url = "https://cdn.example.org/archive/final-name.json"

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={"Link": f'<{data_url}>; rel="item"'},
            request=httpx.Request("HEAD", landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(200, text="<html></html>", request=httpx.Request("GET", landing))
    )

    respx.get(data_url).mock(
        return_value=httpx.Response(
            302,
            headers={"Location": final_url},
            request=httpx.Request("GET", data_url),
        )
    )
    respx.get(final_url).mock(
        return_value=httpx.Response(
            200,
            content=b"payload",
            request=httpx.Request("GET", final_url),
        )
    )

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 1
    assert (tmp_path / "final-name.json").read_bytes() == b"payload"