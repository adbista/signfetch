from pathlib import Path

import httpx
import respx

from signfetch import download_data


@respx.mock

def test_download_data_harvests_http_html_and_linkset_items_and_deduplicates(tmp_path: Path) -> None:
    landing = 'https://example.org/record'
    linkset = 'https://example.org/linkset.json'
    data_a = 'https://example.org/files/a.csv'
    data_b = 'https://example.org/files/b.csv'
    data_c = 'https://example.org/files/c.zip'

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={
                'Link': f'<{data_a}>; rel="item"; type="text/csv", <{linkset}>; rel="linkset"; type="application/linkset+json"'
            },
            request=httpx.Request('HEAD', landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(
            200,
            headers={
                'Content-Type': 'text/html',
                'Link': f'<{data_a}>; rel="item"; type="text/csv"'
            },
            text=f'''
                <html><head>
                <link rel="item" href="{data_b}" type="text/csv">
                <link rel="linkset" href="{linkset}" type="application/linkset+json">
                </head><body>record</body></html>
            ''',
            request=httpx.Request('GET', landing),
        )
    )
    respx.get(linkset).mock(
        return_value=httpx.Response(
            200,
            headers={'Content-Type': 'application/linkset+json'},
            json={
                'linkset': [
                    {
                        'item': [
                            {'href': data_c, 'type': 'application/zip'},
                            {'href': data_b, 'type': 'text/csv'},
                        ]
                    }
                ]
            },
            request=httpx.Request('GET', linkset),
        )
    )
    respx.get(data_a).mock(return_value=httpx.Response(200, content=b'alpha', request=httpx.Request('GET', data_a)))
    respx.get(data_b).mock(return_value=httpx.Response(200, content=b'beta', request=httpx.Request('GET', data_b)))
    respx.get(data_c).mock(return_value=httpx.Response(200, content=b'gamma', request=httpx.Request('GET', data_c)))

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 3
    assert [item.url for item in result.items] == [data_a, data_b, data_c]
    assert (tmp_path / 'a.csv').read_bytes() == b'alpha'
    assert (tmp_path / 'b.csv').read_bytes() == b'beta'
    assert (tmp_path / 'c.zip').read_bytes() == b'gamma'


@respx.mock

def test_download_data_uses_unique_filenames_when_url_paths_collide(tmp_path: Path) -> None:
    landing = 'https://example.org/record'
    data_a = 'https://example.org/files/report'
    data_b = 'https://example.org/other/report'

    respx.head(landing).mock(
        return_value=httpx.Response(
            200,
            headers={'Link': f'<{data_a}>; rel="item", <{data_b}>; rel="item"'},
            request=httpx.Request('HEAD', landing),
        )
    )
    respx.get(landing).mock(
        return_value=httpx.Response(200, text='<html></html>', request=httpx.Request('GET', landing))
    )
    respx.get(data_a).mock(
        return_value=httpx.Response(
            200,
            headers={'Content-Type': 'text/plain'},
            content=b'one',
            request=httpx.Request('GET', data_a),
        )
    )
    respx.get(data_b).mock(
        return_value=httpx.Response(
            200,
            headers={'Content-Type': 'text/plain'},
            content=b'two',
            request=httpx.Request('GET', data_b),
        )
    )

    result = download_data(landing, output_dir=tmp_path)

    assert result.unique_item_count == 2
    assert (tmp_path / 'report.txt').read_bytes() == b'one'
    assert (tmp_path / 'report_2.txt').read_bytes() == b'two'
