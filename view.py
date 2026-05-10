import glob
import json
import math
import os
import random
import re
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime

import folium

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

STYLE_INTERSECTED = {
    "color": "#27ae60", "fillColor": "#2ecc71", "fillOpacity": 0.5, "weight": 2,
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

def build_intersections(geojson_files):
    intersections = {}
    for path in geojson_files:
        with open(path) as f:
            data = json.load(f)
        for feature in data.get("features", []):
            fid = str(feature.get("id", ""))
            if fid:
                intersections[fid] = random.choice([True, False])

    out = os.path.join(DATA_DIR, "intersections.json")
    with open(out, "w") as f:
        json.dump(intersections, f, indent=2)
    return intersections


def load_intersections():
    path = os.path.join(DATA_DIR, "intersections.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def make_style_fn(intersections):
    def style_fn(feature):
        fid = str(feature.get("id", ""))
        return STYLE_INTERSECTED if intersections.get(fid) else STYLE_DEFAULT
    return style_fn


# ── HTML post-processing ──────────────────────────────────────────────────────

def inject_panel_and_legend(html_path, stats, total_score, intersected_count):
    with open(html_path) as f:
        html = f.read()

    css = """
<style>
  body { margin-left: 300px !important; }
  #side-panel {
    position: fixed; left: 0; top: 0; width: 300px; height: 100vh;
    overflow-y: auto; background: #1e1e2e; color: #cdd6f4;
    padding: 16px; box-sizing: border-box; z-index: 1000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 13px;
  }
  #side-panel h2 { margin: 0 0 14px; font-size: 15px; color: #cba6f7; letter-spacing: .3px; }
  #side-panel h3 { margin: 16px 0 6px; font-size: 11px; color: #89b4fa; text-transform: uppercase; letter-spacing: .8px; }
  .stat-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #313244; }
  .stat-label { color: #a6adc8; }
  .stat-value { font-weight: 600; }
  #legend {
    position: fixed; bottom: 24px; right: 12px; z-index: 1000;
    background: white; padding: 10px 14px; border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 13px;
  }
  #legend .leg-title { font-weight: 600; margin-bottom: 7px; color: #333; }
  .leg-row { display: flex; align-items: center; gap: 7px; margin-bottom: 4px; color: #444; }
  .leg-swatch { width: 14px; height: 14px; border-radius: 3px; flex-shrink: 0; }
  .leaflet-tooltip tr:first-child th { display: none; }
  .leaflet-tooltip tr:first-child td { font-size: 14px; font-weight: 700; padding-bottom: 6px; border-bottom: 1px solid #e0e0e0; }
  .leaflet-tooltip tr:not(:first-child) th { color: #888; font-weight: normal; padding-right: 8px; }
</style>
"""

    panel = f"""
<div id="side-panel">
  <h2>Park Run</h2>

  <h3>Score</h3>
  <div class="stat-row"><span class="stat-label">Total Points</span><span class="stat-value" style="color:#f9e2af">{round(total_score, 1)}</span></div>
  <div class="stat-row"><span class="stat-label">Parcels Hit</span><span class="stat-value">{intersected_count}</span></div>

  <h3>Summary</h3>
  <div class="stat-row"><span class="stat-label">Distance</span><span class="stat-value">{stats['total_km']} km</span></div>
  <div class="stat-row"><span class="stat-label">Time</span><span class="stat-value">{stats['time']}</span></div>
  <div class="stat-row"><span class="stat-label">Avg Pace</span><span class="stat-value">{stats['pace']}</span></div>
  <div class="stat-row"><span class="stat-label">Elevation Gain</span><span class="stat-value">{stats['ele_gain']} m</span></div>
  <div class="stat-row"><span class="stat-label">Min Elevation</span><span class="stat-value">{stats['ele_min']} m</span></div>
  <div class="stat-row"><span class="stat-label">Max Elevation</span><span class="stat-value">{stats['ele_max']} m</span></div>

  <h3>Elevation</h3>
  <canvas id="ele-chart"></canvas>

  <h3>Pace</h3>
  <canvas id="pace-chart"></canvas>
</div>

<div id="legend">
  <div class="leg-title">Land Access</div>
  <div class="leg-row">
    <span class="leg-swatch" style="background:#2ecc71;border:2px solid #27ae60"></span>
    Intersected (scored)
  </div>
  <div class="leg-row">
    <span class="leg-swatch" style="background:#95a5a6;border:2px solid #7f8c8d"></span>
    Not intersected
  </div>
  <div style="margin-top:8px;font-size:11px;color:#888">Points: 20–100 (smaller = more)</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>
(function() {{
  const dist = {json.dumps(stats['chart_dist'])};
  const ele  = {json.dumps(stats['chart_ele'])};
  const pace = {json.dumps(stats['chart_pace'])};

  const gridColor = '#313244';
  const tickColor = '#a6adc8';

  function baseOpts(xLabel, yLabel, reverseY) {{
    return {{
      responsive: true,
      animation: false,
      plugins: {{ legend: {{ display: false }} }},
      elements: {{ point: {{ radius: 0 }} }},
      scales: {{
        x: {{
          ticks: {{ color: tickColor, maxTicksLimit: 5 }},
          grid: {{ color: gridColor }},
          title: {{ display: true, text: xLabel, color: tickColor }},
        }},
        y: {{
          reverse: !!reverseY,
          ticks: {{ color: tickColor }},
          grid: {{ color: gridColor }},
          title: {{ display: true, text: yLabel, color: tickColor }},
        }},
      }},
    }};
  }}

  new Chart(document.getElementById('ele-chart'), {{
    type: 'line',
    data: {{
      labels: dist,
      datasets: [{{
        data: ele,
        borderColor: '#89b4fa',
        backgroundColor: 'rgba(137,180,250,0.15)',
        fill: true, tension: 0.3, borderWidth: 1.5,
      }}],
    }},
    options: baseOpts('km', 'm', false),
  }});

  new Chart(document.getElementById('pace-chart'), {{
    type: 'line',
    data: {{
      labels: dist,
      datasets: [{{
        data: pace,
        borderColor: '#a6e3a1',
        backgroundColor: 'rgba(166,227,161,0.15)',
        fill: true, tension: 0.3, borderWidth: 1.5,
      }}],
    }},
    options: baseOpts('km', 'min/km', true),
  }});
}})();
</script>
"""

    html = html.replace("</head>", css + "</head>", 1)
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

    geojson_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.geojson")))
    intersections = build_intersections(geojson_files)

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
            hit = bool(intersections.get(fid))
            pts_val = parcel_points(props.get("Shape__Area"))
            props["points"] = round(pts_val, 1)
            if hit:
                total_score += pts_val
                intersected_count += 1

        first_props = data["features"][0].get("properties") or {}
        tooltip_fields = []
        if "common_name" in first_props:
            tooltip_fields.append("common_name")
        tooltip_fields.append("points")

        has_name = "common_name" in first_props
        folium.GeoJson(
            data,
            name=name.replace("_", " "),
            style_function=make_style_fn(intersections),
            tooltip=folium.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=(["", "Points:"] if has_name else ["Points:"]),
                style=(
                    "font-family: sans-serif; font-size: 13px;"
                    " background: white; border-radius: 6px; padding: 8px 10px;"
                ),
                sticky=False,
            ),
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
