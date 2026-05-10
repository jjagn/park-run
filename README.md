# park-run

Downloads public access area data for New Zealand from the [Public Access Areas FeatureServer](https://services2.arcgis.com/b5ADKIcWivL5vNaV/arcgis/rest/services/Public_Access_Areas/FeatureServer).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python download_public_access_areas.py
```

This downloads all 6 layers as GeoJSON files and the descriptions table as JSON:

| File | Description |
|------|-------------|
| `Road_Parcels.geojson` | Road parcels with public access (not downloaded by default) |
| `Easements.geojson` | Easement areas |
| `Reserve_Land.geojson` | Reserve land |
| `Public_Access_Conservation_Land.geojson` | Conservation land with public access |
| `Other_Parks_and_Reserves.geojson` | Other parks and reserves |
| `Other_Public_Access_Areas.geojson` | Other public access areas |
| `PAA_Descriptions.json` | Descriptions table |

All geometries are in WGS84 (EPSG:4326).
