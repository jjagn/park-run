#!/usr/bin/env python3
"""
Downloads missing NZ public access area layers from ArcGIS FeatureServer.
Idempotent — skips layers that already exist in --data-dir.

Usage: python download.py --data-dir <dir>
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

BASE_URL = (
    "https://services2.arcgis.com/b5ADKIcWivL5vNaV/arcgis/rest/services"
    "/Public_Access_Areas/FeatureServer"
)
PAGE_SIZE = 2000
LAYERS = [
    (2, "Easements"),
    (3, "Reserve_Land"),
    (4, "Public_Access_Conservation_Land"),
    (5, "Other_Parks_and_Reserves"),
    (6, "Other_Public_Access_Areas"),
]


def get_count(layer_id: int) -> int:
    r = requests.get(
        f"{BASE_URL}/{layer_id}/query",
        params={"where": "1=1", "returnCountOnly": "true", "f": "json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["count"]


def download_layer(layer_id: int, name: str) -> dict:
    print(f"Downloading {name}…", file=sys.stderr)
    total = get_count(layer_id)
    print(f"  {total} features", file=sys.stderr)
    features, crs, offset = [], None, 0
    while offset < total:
        r = requests.get(
            f"{BASE_URL}/{layer_id}/query",
            params={
                "where": "1=1", "outFields": "*", "returnGeometry": "true",
                "resultOffset": offset, "resultRecordCount": PAGE_SIZE,
                "f": "geojson", "outSR": "4326",
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        batch = data.get("features", [])
        features.extend(batch)
        if crs is None:
            crs = data.get("crs")
        offset += len(batch)
        print(f"  {min(offset, total)}/{total}", file=sys.stderr)
        if not batch or offset >= total:
            break
        time.sleep(0.2)
    return {"type": "FeatureCollection", "crs": crs, "features": features}


def ensure_cache(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    missing = [(lid, n) for lid, n in LAYERS if not (data_dir / f"{n}.geojson").exists()]
    if not missing:
        return
    for layer_id, name in missing:
        data = download_layer(layer_id, name)
        out = data_dir / f"{name}.geojson"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f)
        print(f"Saved {out}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    ensure_cache(Path(parser.parse_args().data_dir))
