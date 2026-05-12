# park-run

A web app for scoring GPX running routes based on how much New Zealand public access land they cover.

Upload a GPX file, get an interactive map showing which public access parcels your run passed through, a score, and stats. Previous runs are stored and browsable.

Public access data is sourced from the [Public Access Areas FeatureServer](https://services2.arcgis.com/b5ADKIcWivL5vNaV/arcgis/rest/services/Public_Access_Areas/FeatureServer).

## Stack

- **Frontend** — React + TypeScript + Vite, React Leaflet, Chart.js
- **Backend** — Node.js + Express + TypeScript
- **Analysis** — TypeScript (Turf.js, fast-xml-parser)
- **Database** — SQLite via Node's built-in `node:sqlite`

## Setup

Requires [pnpm](https://pnpm.io). Install dependencies from the repo root:

```bash
pnpm install
```

## Running

Start both servers in parallel:

```bash
pnpm dev
```

Or individually:

```bash
cd backend && pnpm dev   # port 3001
cd frontend && pnpm dev  # port 5173
```

Then open `http://localhost:5173`.

## How scoring works

Each intersected parcel scores between 20 and 100 points using an exponential falloff — smaller parcels score more. The score thresholds and buffer radius are configurable constants at the top of `backend/src/analysis/analyze.ts`.
