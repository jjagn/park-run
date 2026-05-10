import xml.etree.ElementTree as ET

import shapely.geometry as sg
from pyproj import Transformer
from shapely.ops import transform

NZTM = "EPSG:2193"
WGS84 = "EPSG:4326"

GPX_NS = "http://www.topografix.com/GPX/1/1"


def gpx_bounding_box(gpx_path) -> tuple[float, float, float, float]:
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    lats = [float(pt.attrib["lat"]) for pt in root.iter(f"{{{GPX_NS}}}trkpt")]
    lons = [float(pt.attrib["lon"]) for pt in root.iter(f"{{{GPX_NS}}}trkpt")]
    if not lats:
        raise ValueError(f"No track points found in {gpx_path}")
    return min(lons), min(lats), max(lons), max(lats)


def buffer_track(track: sg.LineString, buffer_meters: float) -> sg.Polygon:
    to_nztm = Transformer.from_crs(WGS84, NZTM, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(NZTM, WGS84, always_xy=True).transform
    projected = transform(to_nztm, track)
    buffered = projected.buffer(buffer_meters)
    return transform(to_wgs84, buffered)


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
