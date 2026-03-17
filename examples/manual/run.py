from pathlib import Path

from signfetch import download_data


result = download_data(
    "https://doi.org/10.5281/zenodo.4318838",
    output_dir=Path("downloads"),
)
print(result)
