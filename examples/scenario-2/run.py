import os
from pathlib import Path

from signfetch import download_data


target = os.environ.get("SIGNFETCH_TARGET", "http://localhost:8000/record")
output_dir = Path(os.environ.get("SIGNFETCH_OUTPUT", "downloads"))
result = download_data(target, output_dir=output_dir)
print(result.unique_item_count)
