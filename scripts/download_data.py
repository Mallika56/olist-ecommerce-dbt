"""Download the 9 Olist CSVs into data/raw/ and verify them.

Default source: a public GitHub copy pinned to one commit, checked file-by-file
against SHA-256 hashes of the original Kaggle release (so you know it's untouched).

    python scripts/download_data.py              # GitHub mirror (no login needed)
    python scripts/download_data.py --kaggle     # official Kaggle source (needs ~/.kaggle/kaggle.json)

Dataset: "Brazilian E-Commerce Public Dataset by Olist", Kaggle, CC BY-NC-SA 4.0.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

MIRROR = ("https://raw.githubusercontent.com/cardonajsebas/olist-data-warehouse/"
          "cf5c307e1c806dc2b8dd163f5d0153607410e13f/datasets/{folder}/{name}")

# file -> (folder in the mirror repo, sha256 of the original Kaggle file)
FILES = {
    "olist_customers_dataset.csv":       ("crm", "983a422239e1712ded753b3bf9ecf47dc73f144d306029dcfa99e70a226883d2"),
    "olist_order_reviews_dataset.csv":   ("crm", "012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7"),
    "olist_geolocation_dataset.csv":     ("erp", "b514f6fc991b9566aeba02aa5d67e2c3630f034b60a0e05aa0d082a3b66d88d6"),
    "olist_order_items_dataset.csv":     ("erp", "0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279"),
    "olist_order_payments_dataset.csv":  ("erp", "4f713964f2815dbbaa40b9488268c55aac3627bfce5aa96cf58d1f3616de3cc0"),
    "olist_orders_dataset.csv":          ("erp", "8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf"),
    "olist_products_dataset.csv":        ("erp", "3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc"),
    "olist_sellers_dataset.csv":         ("erp", "1f643d2b950373b85735e7794b20986f528d7a000432e7c6f9bcbb44d0846a0e"),
    "product_category_name_translation.csv": ("erp", "a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278"),
}


def sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file, read in 1 MiB chunks."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify() -> bool:
    """Check every file in data/raw/ against its expected SHA-256, printing per-file status."""
    ok = True
    for name, (_, expected) in FILES.items():
        path = RAW / name
        if not path.exists():
            print(f"  missing   {name}")
            ok = False
        elif sha256(path) != expected:
            print(f"  MISMATCH  {name}")
            ok = False
        else:
            print(f"  ok        {name}")
    return ok


def from_mirror() -> None:
    """Download any file missing from data/raw/ or whose checksum doesn't match yet."""
    for name, (folder, expected) in FILES.items():
        path = RAW / name
        if path.exists() and sha256(path) == expected:
            continue
        print(f"downloading {name}")
        urllib.request.urlretrieve(MIRROR.format(folder=folder, name=name), path)


def from_kaggle() -> None:
    """Download the dataset via the Kaggle CLI (requires ~/.kaggle/kaggle.json)."""
    subprocess.run(["kaggle", "datasets", "download", "-d", "olistbr/brazilian-ecommerce",
                    "-p", str(RAW), "--unzip"], check=True)


def main() -> None:
    """Parse CLI args, download via the chosen source, then verify checksums."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kaggle", action="store_true", help="download from Kaggle instead of the mirror")
    args = p.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    from_kaggle() if args.kaggle else from_mirror()
    print("verifying checksums:")
    if not verify():
        sys.exit("checksum verification failed")
    print("all 9 files verified")


if __name__ == "__main__":
    main()
