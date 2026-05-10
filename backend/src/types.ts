export interface RunStats {
  total_km: number
  time: string
  pace: string
  ele_gain: number
  ele_min: number | null
  ele_max: number | null
  chart_dist: number[]
  chart_ele: (number | null)[]
  chart_pace: (number | null)[]
}

export interface Feature {
  id: string | number
  name: string
  layer: string
  area_m2: number
  distance_through_m: number
  points: number
  geometry: object
}

export interface AnalysisResult {
  track: [number, number][]
  buffer: object
  stats: RunStats
  features: Feature[]
  total_score: number
  intersected_count: number
}

export interface Run {
  id: number
  name: string
  created_at: string
  total_km: number
  time_str: string
  pace_str: string
  ele_gain: number
  intersected_count: number
  total_score: number
}
