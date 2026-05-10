import { useEffect, useRef } from 'react'
import L from 'leaflet'
import type { AnalysisResult, Feature } from '../types'
import styles from './RunMap.module.css'

interface Props {
  result: AnalysisResult
}

function featureStyle(f: Feature): L.PathOptions {
  if (f.distance_through_m > 0) {
    return { color: '#689d6a', fillColor: '#8ec07c', fillOpacity: 0.5, weight: 2 }
  }
  return { color: '#d65d0e', fillColor: '#fe8019', fillOpacity: 0.4, weight: 2 }
}

export function RunMap({ result }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const lats = result.track.map(p => p[0])
    const lons = result.track.map(p => p[1])
    const center: L.LatLngTuple = [
      (Math.min(...lats) + Math.max(...lats)) / 2,
      (Math.min(...lons) + Math.max(...lons)) / 2,
    ]

    const map = L.map(containerRef.current).setView(center, 15)
    mapRef.current = map

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap contributors © CARTO',
      maxZoom: 19,
    }).addTo(map)

    // Buffer region
    L.geoJSON(result.buffer as GeoJSON.GeoJsonObject, {
      style: { color: '#fb4934', fillColor: '#fb4934', fillOpacity: 0.12, weight: 1 },
    }).addTo(map)

    // Visited parcels
    result.features.forEach(f => {
      L.geoJSON(f.geometry as GeoJSON.GeoJsonObject, {
        style: featureStyle(f),
      })
        .bindTooltip(
          `<strong>${f.name}</strong><br>${f.points} pts · ${f.distance_through_m} m through`,
          { sticky: true },
        )
        .addTo(map)
    })

    // Track
    L.polyline(result.track, { color: '#fb4934', weight: 3, opacity: 0.9 }).addTo(map)

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [result])

  return <div ref={containerRef} className={styles.map} />
}
