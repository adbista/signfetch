# signfetch v0.1

Python package focused on **downloading data discovered via FAIR Signposting**.

## Scope

Version `0.1.0` intentionally focuses on one public API:

- `download_data(target, output_dir=...)`

The function discovers `item` links from the three main Signposting delivery mechanisms:

1. HTTP `Link` headers
2. HTML `<link>` elements
3. Link Sets discoverable with the `linkset` relation

It then deduplicates discovered data URLs and downloads all unique resources.

## Install

```bash
pip install .
```

For development:

```bash
pip install -e .[dev]
```

## Example

```python
from pathlib import Path
from signfetch import download_data

result = download_data(
    "https://doi.org/10.5281/zenodo.1000000",
    output_dir=Path("downloads")
)

print(result.unique_item_count)
for item in result.items:
    print(item.url, item.saved_path)
```

## Design notes

Main components:
- `SignpostingHarvester` discovers `item` and `linkset` links
- `LinkHeaderParser`, `HtmlLinkParser`, `LinksetParser` parse representations
- `DataDownloader` downloads discovered resources
- `download_data()` is the small public façade


## Docker

Build:

```bash
docker build -t signfetch:0.1.0 .
```

Run tests in the image:

```bash
docker run --rm signfetch:0.1.0 pytest
```
