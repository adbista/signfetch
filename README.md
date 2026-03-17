# signfetch v0.2.0a1

Python package focused on **discovering and downloading data via FAIR Signposting**.

## Scope

Version `0.2.0a1` exposes two public APIs:

* `list_item_links(target)` – discover `item` links without downloading
* `download_data(target, output_dir=...)` – discover and download data resources

Both functions use FAIR Signposting discovery mechanisms.

The package discovers `item` links from the three main Signposting delivery mechanisms:

1. HTTP `Link` headers
2. HTML `<link>` elements
3. Link Sets discoverable with the `linkset` relation

Link sets are automatically retrieved and parsed when present.

---

# Example – discover data resources

You can inspect available data resources without downloading them.

```python
from signfetch import list_item_links

links = list_item_links(
    "https://doi.org/10.5281/zenodo.12542566"
)

for link in links:
    print(link.url, link.source)
```
---

# Example – download discovered data

`download_data()` performs discovery and downloads all discovered resources.

```python
from pathlib import Path
from signfetch import download_data

result = download_data(
    "https://doi.org/10.5281/zenodo.12542566",
    output_dir=Path("downloads")
)

print(result.unique_item_count)

for item in result.items:
    print(item.url, item.saved_path)
```
---

# Design notes

Main components:

**Signposting discovery**

* `SignpostingHarvester` – orchestrates discovery
* `LinkHeaderParser` – parses HTTP `Link` headers
* `HtmlLinkParser` – parses HTML `<link>` elements
* `LinksetParser` – parses linkset documents

**Downloading**

* `DataDownloader` – downloads resources discovered via `item` links
* downloads are executed concurrently

**Public API**

* `list_item_links()` – discovery only
* `download_data()` – discovery + download

---

# Installation

```bash
pip install signfetch
```


