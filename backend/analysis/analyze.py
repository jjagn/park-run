#!/usr/bin/env python3
"""
Analysis bridge — reads a GPX, analyzes it against NZ public access areas,
and writes a single JSON object to stdout.

Usage: python analyze.py --gpx <path> --data-dir <dir>
"""
import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import shapely.geometry as sg
from pyproj import Transformer
from shapely.ops import transform

NZTM = "EPSG:2193"
WGS84 = "EPSG:4326"
GPX_NS = "http://www.topografix.com/GPX/1/1"
GPX_BUFFER_METERS = 1
LAYERS = [
    "Easements",
    "Reserve_Land",
    "Public_Access_Conservation_Land",
    "Other_Parks_and_Reserves",
    "Other_Public_Access_Areas",
]

_SCORE_ALPHA = math.log(100 / 20) / math.log(1e6)


# ── Scoring ───────────────────────────────────────────────────────────────────

def parcel_points(area_m2: float) -> float:
    if not area_m2 or area_m2 <= 0:
        return 20.0
    return max(20.0, min(100.0, 100.0 * area_m2 ** -_SCORE_ALPHA))


# ── GPX parsing ───────────────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_gpx(path: Path):
    root = ET.parse(path).getroot()
    pts = []
    for pt in root.iter(f"{{{GPX_NS}}}trkpt"):
        lat, lon = float(pt.attrib["lat"]), float(pt.attrib["lon"])
        ele_el = pt.find(f"{{{GPX_NS}}}ele")
        time_el = pt.find(f"{{{GPX_NS}}}time")
        pts.append({
            "lat": lat, "lon": lon,
            "ele": float(ele_el.text) if ele_el is not None else None,
            "time": (datetime.fromisoformat(time_el.text.replace("Z", "+00:00"))
                     if time_el is not None else None),
        })
    if not pts:
        raise ValueError(f"No track points found in {path}")
    return pts


def gpx_stats(pts):
    cum_km = [0.0]
    for i in range(1, len(pts)):
        cum_km.append(cum_km[-1] + haversine(
            pts[i-1]["lat"], pts[i-1]["lon"], pts[i]["lat"], pts[i]["lon"]
        ) / 1000)
    total_km = cum_km[-1]

    t0, t1 = pts[0]["time"], pts[-1]["time"]
    if t0 and t1:
        total_secs = (t1 - t0).total_seconds()
        h, rem = divmod(int(total_secs), 3600)
        m, s = divmod(rem, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
    else:
        total_secs, time_str = None, "N/A"

    if total_secs and total_km > 0:
        spm = total_secs / total_km
        pace_str = f"{int(spm // 60)}:{int(spm % 60):02d} /km"
    else:
        pace_str = "N/A"

    eles = [p["ele"] for p in pts if p["ele"] is not None]
    ele_gain = sum(
        max(0, pts[i]["ele"] - pts[i-1]["ele"])
        for i in range(1, len(pts))
        if pts[i]["ele"] is not None and pts[i-1]["ele"] is not None
    )

    step = max(1, len(pts) // 500)
    idx = range(0, len(pts), step)
    chart_dist = [round(cum_km[i], 3) for i in idx]
    chart_ele = [pts[i]["ele"] for i in idx]

    win = 30
    chart_pace = []
    for i in idx:
        lo, hi = max(0, i - win), min(len(pts) - 1, i + win)
        dt = (pts[hi]["time"] and pts[lo]["time"]
              and (pts[hi]["time"] - pts[lo]["time"]).total_seconds())
        dk = cum_km[hi] - cum_km[lo]
        chart_pace.append(round(min(dt / dk / 60, 20), 2) if dt and dk > 0 else None)

    return {
        "total_km": round(total_km, 2),
        "time": time_str,
        "pace": pace_str,
        "ele_gain": round(ele_gain, 1),
        "ele_min": round(min(eles), 1) if eles else None,
        "ele_max": round(max(eles), 1) if eles else None,
        "chart_dist": chart_dist,
        "chart_ele": chart_ele,
        "chart_pace": chart_pace,
    }


# ── Geometry ──────────────────────────────────────────────────────────────────

def buffer_track(track: sg.LineString, meters: float) -> sg.Polygon:
    to_nztm = Transformer.from_crs(WGS84, NZTM, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(NZTM, WGS84, always_xy=True).transform
    return transform(to_wgs84, transform(to_nztm, track).buffer(meters))


def get_name(props: dict) -> str:
    for k in ("common_name", "NAME", "name", "reserve_name", "park_name"):
        if props.get(k):
            return props[k]
    return "Unknown"


def find_intersecting(track, track_buffer, geojson, layer_name):
    to_nztm = Transformer.from_crs(WGS84, NZTM, always_xy=True).transform
    results = []
    for i, feat in enumerate(geojson.get("features", [])):
        if not feat.get("geometry"):
            continue
        poly = sg.shape(feat["geometry"])
        if not track_buffer.intersects(poly):
            continue
        intersection = track.intersection(poly)
        area_m2 = transform(to_nztm, poly).area
        dist_m = 0.0 if intersection.is_empty else transform(to_nztm, intersection).length
        props = feat.get("properties") or {}
        results.append({
            "id": feat.get("id", i),
            "name": get_name(props),
            "layer": layer_name,
            "area_m2": round(area_m2, 1),
            "distance_through_m": round(dist_m, 1),
            "points": round(parcel_points(area_m2), 1),
            "geometry": feat["geometry"],
        })
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpx", required=True)
    parser.add_argument("--data-dir", required=True)
    args = parser.parse_args()

    gpx_path = Path(args.gpx)
    data_dir = Path(args.data_dir)

    pts = parse_gpx(gpx_path)
    stats = gpx_stats(pts)
    track = sg.LineString([(p["lon"], p["lat"]) for p in pts])
    track_buffer = buffer_track(track, GPX_BUFFER_METERS)

    features = []
    for name in LAYERS:
        path_ = data_dir / f"{name}.geojson"
        if not path_.exists():
            print(f"Warning: {path_} not found, skipping", file=sys.stderr)
            continue
        with open(path_, encoding="utf-8") as f:
            geojson = json.load(f)
        features.extend(find_intersecting(track, track_buffer, geojson, name))

    total_score = sum(parcel_points(f["area_m2"]) for f in features)

    print(json.dumps({
        "track": [[p["lat"], p["lon"]] for p in pts],
        "buffer": sg.mapping(track_buffer),
        "stats": stats,
        "features": features,
        "total_score": round(total_score, 1),
        "intersected_count": len(features),
    }))


if __name__ == "__main__":
    main()
