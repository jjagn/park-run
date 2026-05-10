# park-run

A web app for scoring GPX running routes based on how much New Zealand public access land they cover.

Upload a GPX file, get an interactive map showing which public access parcels your run passed through, a score, and stats. Previous runs are stored and browsable.

Public access data is sourced from the [Public Access Areas FeatureServer](https://services2.arcgis.com/b5ADKIcWivL5vNaV/arcgis/rest/services/Public_Access_Areas/FeatureServer).

## Stack

- **Frontend** — React + TypeScript + Vite, React Leaflet, Chart.js
- **Backend** — Node.js + Express + TypeScript
- **Analysis** — Python (shapely, pyproj, gpxpy)
- **Database** — SQLite via Node's built-in `node:sqlite`

## Setup

### Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/analysis/requirements.txt
```

### Node dependencies

```bash
cd backend && npm install
cd ../frontend && npm install
```

## Running

Start the backend (port 3001):

```bash
cd backend && npm run dev
```

Start the frontend dev server (port 5173):

```bash
cd frontend && npm run dev
```

Then open `http://localhost:5173`.

## How scoring works

Each intersected parcel scores between 20 and 100 points using an exponential falloff — smaller parcels score more. Parcels where the track buffer overlaps but the track doesn't pass directly through score at half rate.
