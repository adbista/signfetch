from signfetch.parsers import LinkHeaderParser, LinksetParser


def test_link_header_parser_parses_item_links_and_attributes() -> None:
    parser = LinkHeaderParser()
    links = parser.parse(
        ['<data/file.csv>; rel="item"; type="text/csv", <meta.json>; rel="describedby"; type="application/json"'],
        base_url='https://example.org/record',
        source='http-header',
    )

    assert len(links) == 2
    assert links[0].url == 'https://example.org/data/file.csv'
    assert links[0].rel == 'item'
    assert links[0].type == 'text/csv'


def test_linkset_parser_parses_application_linkset_json() -> None:
    parser = LinksetParser()
    links = parser.parse(
        '{"linkset": [{"item": [{"href": "/files/a.csv", "type": "text/csv"}, {"href": "/files/b.csv"}]}]}',
        base_url='https://example.org/links/linkset.json',
        source='linkset',
        content_type='application/linkset+json',
    )

    assert [link.url for link in links] == [
        'https://example.org/files/a.csv',
        'https://example.org/files/b.csv',
    ]
    assert links[0].rel == 'item'
