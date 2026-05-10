"""
Downloads all layers and tables from the Public Access Areas FeatureServer.
https://services2.arcgis.com/b5ADKIcWivL5vNaV/arcgis/rest/services/Public_Access_Areas/FeatureServer
"""

import json
import time
import xml.etree.ElementTree as ET

import requests

from config import BASE_URL, GPX_FILE, LAYERS, OUTPUT_DIR, PAGE_SIZE, TABLES

GPX_NS = "http://www.topografix.com/GPX/1/1"


def gpx_bounding_box(gpx_path) -> tuple[float, float, float, float]:
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    lats = [float(pt.attrib["lat"]) for pt in root.iter(f"{{{GPX_NS}}}trkpt")]
    lons = [float(pt.attrib["lon"]) for pt in root.iter(f"{{{GPX_NS}}}trkpt")]
    if not lats:
        raise ValueError(f"No track points found in {gpx_path}")
    return min(lons), min(lats), max(lons), max(lats)


def build_geometry_params(min_lon, min_lat, max_lon, max_lat) -> dict:
    return {
        "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
    }


def query_layer(layer_id: int, offset: int, count: int, geometry_params: dict, include_geometry: bool = True) -> dict:
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": str(include_geometry).lower(),
        "resultOffset": offset,
        "resultRecordCount": count,
        "f": "geojson" if include_geometry else "json",
        "outSR": "4326",
        **geometry_params,
    }
    url = f"{BASE_URL}/{layer_id}/query"
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def get_feature_count(layer_id: int, geometry_params: dict) -> int:
    params = {
        "where": "1=1",
        "returnCountOnly": "true",
        "f": "json",
        **geometry_params,
    }
    url = f"{BASE_URL}/{layer_id}/query"
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()["count"]


def download_layer(layer_id: int, name: str, geometry_params: dict, is_table: bool = False) -> dict | list:
    label = "table" if is_table else "layer"
    print(f"Fetching {label} {layer_id}: {name}")

    total = get_feature_count(layer_id, geometry_params)
    print(f"  Total records: {total}")

    all_features = []
    crs = None
    offset = 0

    while offset < total:
        batch = query_layer(layer_id, offset, PAGE_SIZE, geometry_params, include_geometry=not is_table)
        features = batch.get("features", [])
        all_features.extend(features)
        if not is_table and crs is None:
            crs = batch.get("crs")
        fetched = len(features)
        offset += fetched
        print(f"  Downloaded {min(offset, total)}/{total}")
        if fetched == 0:
            break
        if offset < total:
            time.sleep(0.2)

    if is_table:
        return all_features

    return {
        "type": "FeatureCollection",
        "crs": crs,
        "features": all_features,
    }


def save(data: dict | list, filename: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"  Saved to {path}")


def main() -> None:
    min_lon, min_lat, max_lon, max_lat = gpx_bounding_box(GPX_FILE)
    print(f"GPX bounding box: ({min_lat:.6f}, {min_lon:.6f}) to ({max_lat:.6f}, {max_lon:.6f})")

    geometry_params = build_geometry_params(min_lon, min_lat, max_lon, max_lat)

    for layer_id, name in LAYERS:
        data = download_layer(layer_id, name, geometry_params, is_table=False)
        save(data, f"{name}.geojson")

    for table_id, name in TABLES:
        data = download_layer(table_id, name, geometry_params, is_table=True)
        save(data, f"{name}.json")

    print("Done.")


if __name__ == "__main__":
    main()
