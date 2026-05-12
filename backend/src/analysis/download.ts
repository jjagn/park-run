import { existsSync, mkdirSync, writeFileSync } from 'fs'
import path from 'path'

const BASE_URL =
  'https://services2.arcgis.com/b5ADKIcWivL5vNaV/arcgis/rest/services/Public_Access_Areas/FeatureServer'

const PAGE_SIZE = 2000

const LAYERS: [number, string][] = [
  [2, 'Easements'],
  [3, 'Reserve_Land'],
  [4, 'Public_Access_Conservation_Land'],
  [5, 'Other_Parks_and_Reserves'],
  [6, 'Other_Public_Access_Areas'],
]

async function getCount(layerId: number): Promise<number> {
  const url = new URL(`${BASE_URL}/${layerId}/query`)
  url.searchParams.set('where', '1=1')
  url.searchParams.set('returnCountOnly', 'true')
  url.searchParams.set('f', 'json')
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Count request failed: ${res.status}`)
  const data = (await res.json()) as { count: number }
  return data.count
}

async function downloadLayer(layerId: number, name: string): Promise<object> {
  console.error(`Downloading ${name}…`)
  const total = await getCount(layerId)
  console.error(`  ${total} features`)

  const features: object[] = []
  let crs: object | null = null
  let offset = 0

  while (offset < total) {
    const url = new URL(`${BASE_URL}/${layerId}/query`)
    url.searchParams.set('where', '1=1')
    url.searchParams.set('outFields', '*')
    url.searchParams.set('returnGeometry', 'true')
    url.searchParams.set('resultOffset', String(offset))
    url.searchParams.set('resultRecordCount', String(PAGE_SIZE))
    url.searchParams.set('f', 'geojson')
    url.searchParams.set('outSR', '4326')

    const res = await fetch(url.toString(), { signal: AbortSignal.timeout(60_000) })
    if (!res.ok) throw new Error(`Layer request failed: ${res.status}`)
    const data = (await res.json()) as { features?: object[]; crs?: object }

    const batch = data.features ?? []
    features.push(...batch)
    if (crs === null && data.crs) crs = data.crs
    offset += batch.length
    console.error(`  ${Math.min(offset, total)}/${total}`)

    if (!batch.length || offset >= total) break
    await new Promise(r => setTimeout(r, 200))
  }

  return { type: 'FeatureCollection', crs, features }
}

export async function ensureCache(dataDir: string): Promise<void> {
  mkdirSync(dataDir, { recursive: true })
  const missing = LAYERS.filter(([, name]) => !existsSync(path.join(dataDir, `${name}.geojson`)))
  if (!missing.length) return

  for (const [layerId, name] of missing) {
    const data = await downloadLayer(layerId, name)
    const out = path.join(dataDir, `${name}.geojson`)
    writeFileSync(out, JSON.stringify(data))
    console.error(`Saved ${out}`)
  }
}
