import { getDb } from '../db.js'
import type { Run } from '../types.js'

interface NewRun {
  name: string
  total_km: number
  time_str: string
  pace_str: string
  ele_gain: number
  intersected_count: number
  total_score: number
}

export const runDao = {
  insert(run: NewRun): number {
    const info = getDb()
      .prepare(
        `INSERT INTO runs (name, total_km, time_str, pace_str, ele_gain, intersected_count, total_score)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(run.name, run.total_km, run.time_str, run.pace_str, run.ele_gain, run.intersected_count, run.total_score)
    return Number(info.lastInsertRowid)
  },

  list(): Run[] {
    return getDb().prepare('SELECT * FROM runs ORDER BY created_at DESC').all() as unknown as Run[]
  },

  get(id: number): Run | null {
    return (getDb().prepare('SELECT * FROM runs WHERE id = ?').get(id) as unknown as Run | undefined) ?? null
  },

  delete(id: number): void {
    getDb().prepare('DELETE FROM runs WHERE id = ?').run(id)
  },
}
