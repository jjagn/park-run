import glob
import json
import os
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

BASE_URL = "https://services2.arcgis.com/b5ADKIcWivL5vNaV/arcgis/rest/services/Public_Access_Areas/FeatureServer"

LAYERS = {
    # 1: "Road_Parcels",
    2: "Easements",
    3: "Reserve_Land",
    4: "Public_Access_Conservation_Land",
    5: "Other_Parks_and_Reserves",
    6: "Other_Public_Access_Areas",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PAGE_SIZE = 2000


def gpx_bbox(gpx_path):
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    ns = {"gpx": "http://www.topografix.com/GPX/1/1"}

    lats, lons = [], []
    for pt in root.findall(".//gpx:trkpt", ns):
        lats.append(float(pt.attrib["lat"]))
        lons.append(float(pt.attrib["lon"]))

    if not lats:
        raise ValueError(f"No track points found in {gpx_path}")

    # Format: minx,miny,maxx,maxy  (lon,lat order for ArcGIS envelope)
    return f"{min(lons)},{min(lats)},{max(lons)},{max(lats)}"


def find_gpx():
    matches = glob.glob(os.path.join(DATA_DIR, "*.gpx"))
    if not matches:
        raise FileNotFoundError(f"No .gpx file found in {DATA_DIR}")
    return matches[0]


def query_layer(layer_id, bbox):
    features = []
    offset = 0

    while True:
        params = urllib.parse.urlencode({
            "where": "1=1",
            "geometry": bbox,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "outSR": "4326",
            "f": "geojson",
            "resultRecordCount": PAGE_SIZE,
            "resultOffset": offset,
        })

        url = f"{BASE_URL}/{layer_id}/query?{params}"

        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())

        page_features = data.get("features", [])
        features.extend(page_features)
        print(f"  Layer {layer_id}: fetched {len(features)} records so far...")

        if len(page_features) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        time.sleep(0.5)  # be polite to the server

    return features


def main():
    gpx_path = find_gpx()
    bbox = gpx_bbox(gpx_path)
    print(f"Using GPX file: {gpx_path}")
    print(f"Bounding box: {bbox}")

    os.makedirs(DATA_DIR, exist_ok=True)

    for layer_id, layer_name in LAYERS.items():
        print(f"Querying layer {layer_id}: {layer_name}")
        features = query_layer(layer_id, bbox)

        geojson = {
            "type": "FeatureCollection",
            "features": features,
        }

        filename = os.path.join(DATA_DIR, f"{layer_name}.geojson")
        with open(filename, "w") as f:
            json.dump(geojson, f)

        print(f"  Saved {len(features)} features to {filename}")


if __name__ == "__main__":
    main()
