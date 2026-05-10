import xml.etree.ElementTree as ET

import shapely.geometry as sg

GPX_NS = "http://www.topografix.com/GPX/1/1"


def gpx_bounding_box(gpx_path) -> tuple[float, float, float, float]:
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    lats = [float(pt.attrib["lat"]) for pt in root.iter(f"{{{GPX_NS}}}trkpt")]
    lons = [float(pt.attrib["lon"]) for pt in root.iter(f"{{{GPX_NS}}}trkpt")]
    if not lats:
        raise ValueError(f"No track points found in {gpx_path}")
    return min(lons), min(lats), max(lons), max(lats)


def load_gpx_track(gpx_path) -> sg.LineString:
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    coords = [
        (float(pt.attrib["lon"]), float(pt.attrib["lat"]))
        for pt in root.iter(f"{{{GPX_NS}}}trkpt")
    ]
    if not coords:
        raise ValueError(f"No track points found in {gpx_path}")
    return sg.LineString(coords)
