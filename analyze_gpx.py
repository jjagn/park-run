"""
Analyzes a GPX track against downloaded NZ public access area GeoJSON layers.
Run download_public_access_areas.py first to populate the data/ directory.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import shapely.geometry as sg
from pyproj import Transformer
from shapely.ops import transform

from config import GPX_BUFFER_METERS, GPX_FILE, LAYERS, OUTPUT_DIR, RESULTS_FILE
from gpxutils import load_gpx_track

NZTM = "EPSG:2193"
WGS84 = "EPSG:4326"


def load_geojson(layer_name: str) -> dict:
    path = OUTPUT_DIR / f"{layer_name}.geojson"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run download_public_access_areas.py first"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def buffer_track(track: sg.LineString, buffer_meters: float) -> sg.Polygon:
    to_nztm = Transformer.from_crs(WGS84, NZTM, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(NZTM, WGS84, always_xy=True).transform
    projected = transform(to_nztm, track)
    buffered = projected.buffer(buffer_meters)
    return transform(to_wgs84, buffered)


def geodesic_length_m(line: sg.base.BaseGeometry, to_nztm) -> float:
    return transform(to_nztm, line).length


def get_feature_name(properties: dict) -> str:
    for key in ("common_name", "NAME", "name", "reserve_name", "park_name"):
        if properties.get(key):
            return properties[key]
    return "Unknown"


def find_intersecting_features(
    track: sg.LineString,
    track_buffer: sg.Polygon,
    geojson: dict,
    layer_name: str,
) -> list[dict]:
    to_nztm = Transformer.from_crs(WGS84, NZTM, always_xy=True).transform
    results = []
    for i, feature in enumerate(geojson.get("features", [])):
        if not feature.get("geometry"):
            continue
        poly = sg.shape(feature["geometry"])
        if not track_buffer.intersects(poly):
            continue
        intersection = track.intersection(poly)
        area_m2 = transform(to_nztm, poly).area
        dist_m = 0.0 if intersection.is_empty else geodesic_length_m(intersection, to_nztm)
        props = feature.get("properties") or {}
        results.append({
            "id": feature.get("id", i),
            "name": get_feature_name(props),
            "layer": layer_name,
            "area_m2": round(area_m2, 1),
            "distance_through_m": round(dist_m, 1),
            "geometry": feature["geometry"],
            "properties": props,
        })
    return results


def compute_stats(visited: list[dict]) -> dict:
    if not visited:
        return {
            "total_reserves_visited": 0,
            "total_distance_through_reserves_m": 0,
            "largest_reserve": None,
            "smallest_reserve": None,
        }
    by_area = sorted(visited, key=lambda x: x["area_m2"])

    def summary(entry):
        return {"name": entry["name"], "layer": entry["layer"], "area_m2": entry["area_m2"]}

    return {
        "total_reserves_visited": len(visited),
        "total_distance_through_reserves_m": round(
            sum(v["distance_through_m"] for v in visited), 1
        ),
        "largest_reserve": summary(by_area[-1]),
        "smallest_reserve": summary(by_area[0]),
    }


def export_results(visited: list[dict], stats: dict, output_path: Path, layer_names: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "gpx_file": str(GPX_FILE),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "layers_checked": layer_names,
            "gpx_buffer_meters": GPX_BUFFER_METERS,
        },
        "stats": stats,
        "visited": visited,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Results written to {output_path}")


def main() -> None:
    track = load_gpx_track(GPX_FILE)
    track_buffer = buffer_track(track, GPX_BUFFER_METERS)
    layer_names = [name for _, name in LAYERS]

    all_visited = []
    for _, name in LAYERS:
        geojson = load_geojson(name)
        features = find_intersecting_features(track, track_buffer, geojson, name)
        print(f"  {name}: {len(features)} reserve(s) visited")
        all_visited.extend(features)

    stats = compute_stats(all_visited)
    export_results(all_visited, stats, RESULTS_FILE, layer_names)


if __name__ == "__main__":
    main()
