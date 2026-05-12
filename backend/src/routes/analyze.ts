import { Router } from 'express'
import multer from 'multer'
import { mkdirSync, writeFileSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'
import { ensureCache } from '../analysis/download.js'
import { analyzeGpx } from '../analysis/analyze.js'
import { runDao } from '../dao/runDao.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.resolve(__dirname, '../../../data')
const RUNS_DIR = path.resolve(__dirname, '../../../runs')

const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 16 * 1024 * 1024 } })
export const analyzeRouter = Router()

analyzeRouter.post('/', upload.single('gpx'), async (req, res) => {
  const name = (req.body.name ?? '').trim()
  const save = req.body.save === 'true'

  if (!name) return void res.status(400).json({ error: 'Run name is required' })
  if (!req.file) return void res.status(400).json({ error: 'No GPX file uploaded' })

  try {
    await ensureCache(DATA_DIR)

    const result = analyzeGpx(req.file.buffer, DATA_DIR)

    if (save) {
      const runId = runDao.insert({
        name,
        total_km: result.stats.total_km,
        time_str: result.stats.time,
        pace_str: result.stats.pace,
        ele_gain: result.stats.ele_gain,
        intersected_count: result.intersected_count,
        total_score: result.total_score,
      })
      const runDir = path.join(RUNS_DIR, String(runId))
      mkdirSync(runDir, { recursive: true })
      writeFileSync(path.join(runDir, 'result.json'), JSON.stringify(result))
      return void res.json({ runId, result })
    }

    res.json({ result })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    res.status(500).json({ error: msg })
  }
})
