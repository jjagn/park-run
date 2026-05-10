from pathlib import Path

BASE_URL = "https://services2.arcgis.com/b5ADKIcWivL5vNaV/arcgis/rest/services/Public_Access_Areas/FeatureServer"
PAGE_SIZE = 2000
OUTPUT_DIR = Path("data")
RESULTS_FILE = Path("results/analysis.json")
GPX_FILE = Path("data/park_run.gpx")
GPX_BUFFER_METERS = 1

# Layers to download (layer_id, output_name)
LAYERS = [
    # Don't download road layers
    # (1, "Road_Parcels"),
    (2, "Easements"),
    (3, "Reserve_Land"),
    (4, "Public_Access_Conservation_Land"),
    (5, "Other_Parks_and_Reserves"),
    (6, "Other_Public_Access_Areas"),
]

# Tables to download (table_id, output_name)
TABLES = [
    (7, "PAA_Descriptions"),
]
