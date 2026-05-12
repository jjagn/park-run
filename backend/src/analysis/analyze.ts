import { readFileSync } from 'fs'
import path from 'path'
import { XMLParser } from 'fast-xml-parser'
import * as turf from '@turf/turf'
import type { Feature, Polygon, MultiPolygon } from 'geojson'
import type { AnalysisResult, RunStats, Feature as AppFeature } from '../types.js'

const GPX_BUFFER_METERS = 1
const SCORE_ALPHA = Math.log(100 / 20) / Math.log(1e6)

const LAYERS = [
  'Easements',
  'Reserve_Land',
  'Public_Access_Conservation_Land',
  'Other_Parks_and_Reserves',
  'Other_Public_Access_Areas',
]

// ── Scoring ────────────────────────────────────────────────────────────────

export function parcelPoints(areaM2: number): number {
  if (!areaM2 || areaM2 <= 0) return 20.0
  return Math.max(20.0, Math.min(100.0, 100.0 * Math.pow(areaM2, -SCORE_ALPHA)))
}

// ── GPX Parsing ────────────────────────────────────────────────────────────

interface GpxPoint {
  lat: number
  lon: number
  ele: number | null
  time: Date | null
}

function parseGpx(gpxBuffer: Buffer): GpxPoint[] {
  const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: '',
    isArray: name => name === 'trkpt' || name === 'trkseg',
    removeNSPrefix: true,
  })
  const doc = parser.parse(gpxBuffer)
  const gpx = doc.gpx ?? doc

  const trk = gpx.trk ?? {}
  const trksegs: any[] = Array.isArray(trk.trkseg) ? trk.trkseg : trk.trkseg ? [trk.trkseg] : []
  const trkpts: any[] = trksegs.flatMap(seg => (Array.isArray(seg.trkpt) ? seg.trkpt : seg.trkpt ? [seg.trkpt] : []))

  if (!trkpts.length) throw new Error('No track points found in GPX')

  return trkpts.map((pt: any) => ({
    lat: parseFloat(pt.lat),
    lon: parseFloat(pt.lon),
    ele: pt.ele != null ? parseFloat(pt.ele) : null,
    time: pt.time ? new Date(pt.time) : null,
  }))
}

function haversine(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6_371_000
  const p1 = (lat1 * Math.PI) / 180
  const p2 = (lat2 * Math.PI) / 180
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function buildCumKm(pts: GpxPoint[]): number[] {
  const cumKm = [0]
  for (let i = 1; i < pts.length; i++) {
    cumKm.push(cumKm[i - 1] + haversine(pts[i - 1].lat, pts[i - 1].lon, pts[i].lat, pts[i].lon) / 1000)
  }
  return cumKm
}

function gpxStats(pts: GpxPoint[], cumKm: number[]): RunStats {
  const totalKm = cumKm[cumKm.length - 1]

  const t0 = pts[0].time
  const t1 = pts[pts.length - 1].time
  let timeStr = 'N/A'
  let totalSecs: number | null = null
  if (t0 && t1) {
    totalSecs = (t1.getTime() - t0.getTime()) / 1000
    const h = Math.floor(totalSecs / 3600)
    const m = Math.floor((totalSecs % 3600) / 60)
    const s = Math.floor(totalSecs % 60)
    timeStr = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  let paceStr = 'N/A'
  if (totalSecs && totalKm > 0) {
    const spm = totalSecs / totalKm
    paceStr = `${Math.floor(spm / 60)}:${String(Math.floor(spm % 60)).padStart(2, '0')} /km`
  }

  const eles = pts.filter(p => p.ele !== null).map(p => p.ele as number)
  const eleGain = pts.slice(1).reduce((sum, p, i) => {
    const prev = pts[i].ele
    const curr = p.ele
    return sum + (curr !== null && prev !== null ? Math.max(0, curr - prev) : 0)
  }, 0)

  const step = Math.max(1, Math.floor(pts.length / 500))
  const idxArr: number[] = []
  for (let i = 0; i < pts.length; i += step) idxArr.push(i)

  const win = 30
  const chartPace = idxArr.map(i => {
    const lo = Math.max(0, i - win)
    const hi = Math.min(pts.length - 1, i + win)
    const dt = pts[hi].time && pts[lo].time
      ? (pts[hi].time!.getTime() - pts[lo].time!.getTime()) / 1000
      : null
    const dk = cumKm[hi] - cumKm[lo]
    return dt && dk > 0 ? Math.round(Math.min(dt / dk / 60, 20) * 100) / 100 : null
  })

  return {
    total_km: Math.round(totalKm * 100) / 100,
    time: timeStr,
    pace: paceStr,
    ele_gain: Math.round(eleGain * 10) / 10,
    ele_min: eles.length ? Math.round(Math.min(...eles) * 10) / 10 : null,
    ele_max: eles.length ? Math.round(Math.max(...eles) * 10) / 10 : null,
    chart_dist: idxArr.map(i => Math.round(cumKm[i] * 1000) / 1000),
    chart_ele: idxArr.map(i => pts[i].ele),
    chart_pace: chartPace,
  }
}

// ── Geometry ────────────────────────────────────────────────────────────────

function getFeatureName(props: Record<string, unknown>): string {
  for (const k of ['common_name', 'NAME', 'name', 'reserve_name', 'park_name']) {
    if (props[k]) return String(props[k])
  }
  return 'Unknown'
}

// Estimates the length of track that passes through the polygon by checking
// each segment's endpoints. Approximates partial segments as half-length.
function trackIntersectionLength(
  pts: GpxPoint[],
  cumKm: number[],
  poly: Feature<Polygon | MultiPolygon>,
): number {
  let totalM = 0
  for (let i = 0; i < pts.length - 1; i++) {
    const aIn = turf.booleanPointInPolygon([pts[i].lon, pts[i].lat], poly)
    const bIn = turf.booleanPointInPolygon([pts[i + 1].lon, pts[i + 1].lat], poly)
    const segM = (cumKm[i + 1] - cumKm[i]) * 1000
    if (aIn && bIn) totalM += segM
    else if (aIn || bIn) totalM += segM / 2
  }
  return totalM
}

interface GeoJsonCollection {
  features?: Array<{
    geometry: object | null
    properties?: Record<string, unknown>
    id?: string | number
  }>
}

function findIntersecting(
  pts: GpxPoint[],
  cumKm: number[],
  trackBuffer: Feature<Polygon>,
  geojson: GeoJsonCollection,
  layerName: string,
): AppFeature[] {
  const results: AppFeature[] = []
  for (let i = 0; i < (geojson.features?.length ?? 0); i++) {
    const feat = geojson.features![i]
    if (!feat.geometry) continue

    const poly = { type: 'Feature', geometry: feat.geometry, properties: {} } as Feature<Polygon | MultiPolygon>

    try {
      if (!turf.booleanIntersects(trackBuffer, poly)) continue
    } catch {
      continue
    }

    const areaM2 = turf.area(poly)
    const distM = trackIntersectionLength(pts, cumKm, poly)
    const props = feat.properties ?? {}

    results.push({
      id: feat.id ?? i,
      name: getFeatureName(props),
      layer: layerName,
      area_m2: Math.round(areaM2 * 10) / 10,
      distance_through_m: Math.round(distM * 10) / 10,
      points: Math.round(parcelPoints(areaM2) * 10) / 10,
      geometry: feat.geometry,
    })
  }
  return results
}

// ── Entry point ────────────────────────────────────────────────────────────

export function analyzeGpx(gpxBuffer: Buffer, dataDir: string): AnalysisResult {
  const pts = parseGpx(gpxBuffer)
  const cumKm = buildCumKm(pts)
  const stats = gpxStats(pts, cumKm)

  const trackLine = turf.lineString(pts.map(p => [p.lon, p.lat]))
  const bufferResult = turf.buffer(trackLine, GPX_BUFFER_METERS, { units: 'meters' })
  if (!bufferResult) throw new Error('Failed to compute track buffer')
  const trackBuffer = bufferResult as Feature<Polygon>

  const features: AppFeature[] = []
  for (const name of LAYERS) {
    const filePath = path.join(dataDir, `${name}.geojson`)
    let geojson: GeoJsonCollection
    try {
      geojson = JSON.parse(readFileSync(filePath, 'utf-8'))
    } catch {
      console.error(`Warning: ${filePath} not found, skipping`)
      continue
    }
    features.push(...findIntersecting(pts, cumKm, trackBuffer, geojson, name))
  }

  const totalScore = features.reduce((sum, f) => sum + parcelPoints(f.area_m2), 0)

  return {
    track: pts.map(p => [p.lat, p.lon]),
    buffer: trackBuffer.geometry,
    stats,
    features,
    total_score: Math.round(totalScore * 10) / 10,
    intersected_count: features.length,
  }
}
