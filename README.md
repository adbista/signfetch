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

## Release flow

Use prerelease first (for example `0.1.1a1`) and tag the commit:

```bash
git tag v0.1.1a1
git push origin v0.1.1a1
```

Run CI first. At the end of CI (`package-artifact` job) you will get the artifact `signfetch-package`.
Use that CI run ID in the `publish` workflow input `ci_run_id`.

Validate package and tag without publishing:

```bash
bash scripts/publish_testpypi.sh check
```

Publish to TestPyPI:

```bash
bash scripts/publish_testpypi.sh test
```

Publish to PyPI:

```bash
bash scripts/publish_testpypi.sh prod
```

Recommendation: one artifact build on Linux is enough here because the package is pure Python (`py3-none-any`).
Cross-platform safety is still covered by build checks and unit tests on Linux/Windows/macOS in CI.
