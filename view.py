import glob
import json
import math
import os
import re
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime

import folium
import shapely.geometry as sg

from config import GPX_BUFFER_METERS
from gpxutils import buffer_track

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "results", "analysis.json")
TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "panel_template.html")

STYLE_INTERSECTED = {
    "color": "#27ae60", "fillColor": "#2ecc71", "fillOpacity": 0.5, "weight": 2,
}
STYLE_BUFFER_ONLY = {
    "color": "#d35400", "fillColor": "#e67e22", "fillOpacity": 0.4, "weight": 2,
}
STYLE_DEFAULT = {
    "color": "#7f8c8d", "fillColor": "#95a5a6", "fillOpacity": 0.2, "weight": 1,
}


# ── GPX parsing ───────────────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_gpx(path):
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"gpx": "http://www.topografix.com/GPX/1/1"}

    pts = []
    for pt in root.findall(".//gpx:trkpt", ns):
        lat = float(pt.attrib["lat"])
        lon = float(pt.attrib["lon"])
        ele_el = pt.find("gpx:ele", ns)
        time_el = pt.find("gpx:time", ns)
        ele = float(ele_el.text) if ele_el is not None else None
        t = datetime.fromisoformat(time_el.text.replace("Z", "+00:00")) if time_el is not None else None
        pts.append({"lat": lat, "lon": lon, "ele": ele, "time": t})
    return pts


def gpx_stats(pts):
    # Cumulative distance
    cum_km = [0.0]
    for i in range(1, len(pts)):
        d = haversine(pts[i-1]["lat"], pts[i-1]["lon"], pts[i]["lat"], pts[i]["lon"])
        cum_km.append(cum_km[-1] + d / 1000)

    total_km = cum_km[-1]

    # Time
    t0, t1 = pts[0]["time"], pts[-1]["time"]
    if t0 and t1:
        total_secs = (t1 - t0).total_seconds()
        h, rem = divmod(int(total_secs), 3600)
        m, s = divmod(rem, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
    else:
        total_secs, time_str = None, "N/A"

    # Pace
    if total_secs and total_km > 0:
        spm = total_secs / total_km
        pace_str = f"{int(spm // 60)}:{int(spm % 60):02d} /km"
    else:
        pace_str = "N/A"

    # Elevation
    eles = [p["ele"] for p in pts if p["ele"] is not None]
    ele_gain = sum(
        max(0, pts[i]["ele"] - pts[i-1]["ele"])
        for i in range(1, len(pts))
        if pts[i]["ele"] is not None and pts[i-1]["ele"] is not None
    )

    # Chart data — sample to ≤500 points
    step = max(1, len(pts) // 500)
    idx = range(0, len(pts), step)
    chart_dist = [round(cum_km[i], 3) for i in idx]
    chart_ele = [pts[i]["ele"] for i in idx]

    # Pace chart: rolling window
    win = 30
    chart_pace = []
    for i in idx:
        lo, hi = max(0, i - win), min(len(pts) - 1, i + win)
        dt = pts[hi]["time"] and pts[lo]["time"] and (pts[hi]["time"] - pts[lo]["time"]).total_seconds()
        dk = cum_km[hi] - cum_km[lo]
        if dt and dk > 0:
            chart_pace.append(round(min(dt / dk / 60, 20), 2))
        else:
            chart_pace.append(None)

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


# ── Scoring ───────────────────────────────────────────────────────────────────

# Exponential falloff: 100 pts at 1 m², 20 pts at 1 km² (1e6 m²)
_SCORE_ALPHA = math.log(100 / 20) / math.log(1e6)


def parcel_points(area_m2):
    if not area_m2 or area_m2 <= 0:
        return 20.0
    return max(20.0, min(100.0, 100.0 * area_m2 ** -_SCORE_ALPHA))


# ── Intersection data ─────────────────────────────────────────────────────────

def load_intersections():
    if not os.path.exists(RESULTS_FILE):
        raise FileNotFoundError(
            f"{RESULTS_FILE} not found — run analyze_gpx.py first"
        )
    with open(RESULTS_FILE) as f:
        data = json.load(f)
    return {str(v["id"]): v["distance_through_m"] for v in data.get("visited", [])}


def make_style_fn(intersections):
    def style_fn(feature):
        fid = str(feature.get("id", ""))
        if fid not in intersections:
            return STYLE_DEFAULT
        return STYLE_INTERSECTED if intersections[fid] > 0 else STYLE_BUFFER_ONLY
    return style_fn


# ── HTML post-processing ──────────────────────────────────────────────────────

def inject_panel_and_legend(html_path, stats, total_score, intersected_count):
    with open(html_path) as f:
        html = f.read()

    with open(TEMPLATE_FILE) as f:
        panel = f.read()

    panel = (
        panel
        .replace("__TOTAL_SCORE__", str(round(total_score, 1)))
        .replace("__INTERSECTED_COUNT__", str(intersected_count))
        .replace("__TOTAL_KM__", str(stats["total_km"]))
        .replace("__TIME__", stats["time"])
        .replace("__PACE__", stats["pace"])
        .replace("__ELE_GAIN__", str(stats["ele_gain"]))
        .replace("__ELE_MIN__", str(stats["ele_min"]))
        .replace("__ELE_MAX__", str(stats["ele_max"]))
        .replace("__DIST_DATA__", json.dumps(stats["chart_dist"]))
        .replace("__ELE_DATA__", json.dumps(stats["chart_ele"]))
        .replace("__PACE_DATA__", json.dumps(stats["chart_pace"]))
    )

    html = re.sub(r"(<body[^>]*>)", r"\1" + panel, html, count=1)

    with open(html_path, "w") as f:
        f.write(html)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    gpx_files = glob.glob(os.path.join(DATA_DIR, "*.gpx"))
    if not gpx_files:
        raise FileNotFoundError(f"No .gpx file found in {DATA_DIR}")

    pts = parse_gpx(gpx_files[0])
    stats = gpx_stats(pts)
    track = [(p["lat"], p["lon"]) for p in pts]

    track_line = sg.LineString([(p["lon"], p["lat"]) for p in pts])
    track_buffer = buffer_track(track_line, GPX_BUFFER_METERS)

    geojson_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.geojson")))
    intersections = load_intersections()

    m = folium.Map(location=(
        sum(p["lat"] for p in pts) / len(pts),
        sum(p["lon"] for p in pts) / len(pts),
    ), zoom_start=15, tiles="CartoDB positron")

    total_score = 0.0
    intersected_count = 0

    for geojson_path in geojson_files:
        name = os.path.splitext(os.path.basename(geojson_path))[0]

        with open(geojson_path) as f:
            data = json.load(f)

        if not data.get("features"):
            continue

        for feature in data["features"]:
            fid = str(feature.get("id", ""))
            props = feature.get("properties") or {}
            feature["properties"] = props
            hit = fid in intersections
            pts_val = parcel_points(props.get("Shape__Area"))
            props["points"] = round(pts_val, 1)
            props["distance_through_m"] = intersections[fid] if hit else ""
            if hit:
                total_score += pts_val
                intersected_count += 1

        first_props = data["features"][0].get("properties") or {}
        tooltip_fields = []
        aliases = []
        if "common_name" in first_props:
            tooltip_fields.append("common_name")
            aliases.append("")
        tooltip_fields += ["points", "distance_through_m"]
        aliases += ["Points:", "Through (m):"]

        folium.GeoJson(
            data,
            name=name.replace("_", " "),
            style_function=make_style_fn(intersections),
            tooltip=folium.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=aliases,
                style=(
                    "font-family: sans-serif; font-size: 13px;"
                    " background: white; border-radius: 6px; padding: 8px 10px;"
                ),
                sticky=False,
            ),
        ).add_to(m)

    folium.GeoJson(
        sg.mapping(track_buffer),
        name="Track buffer",
        style_function=lambda _: {
            "color": "#e74c3c", "fillColor": "#e74c3c", "fillOpacity": 0.15, "weight": 1,
        },
    ).add_to(m)
    folium.PolyLine(track, color="#e74c3c", weight=3, opacity=0.9, tooltip="Park run route").add_to(m)
    folium.LayerControl().add_to(m)

    out = os.path.join(os.path.dirname(__file__), "map.html")
    m.save(out)
    inject_panel_and_legend(out, stats, total_score, intersected_count)

    print(f"Saved to {out}")
    webbrowser.open(f"file://{out}")


if __name__ == "__main__":
    main()
