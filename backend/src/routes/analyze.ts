import { Router } from 'express'
import multer from 'multer'
import { spawn } from 'child_process'
import { existsSync, writeFileSync, mkdirSync, rmSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'
import os from 'os'
import { getDb } from '../db.js'
import type { AnalysisResult } from '../types.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ANALYSIS_DIR = path.resolve(__dirname, '../../analysis')
const DATA_DIR = path.resolve(__dirname, '../../../data')
const RUNS_DIR = path.resolve(__dirname, '../../../runs')
const VENV_PYTHON = path.resolve(__dirname, '../../../.venv/bin/python')
const PYTHON = process.env.PYTHON ?? (existsSync(VENV_PYTHON) ? VENV_PYTHON : 'python3')

const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 16 * 1024 * 1024 } })
export const analyzeRouter = Router()

function run(cmd: string, args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    let stdout = ''
    let stderr = ''
    const proc = spawn(cmd, args)
    proc.stdout.on('data', (d: Buffer) => { stdout += d })
    proc.stderr.on('data', (d: Buffer) => { stderr += d })
    proc.on('close', code => {
      if (code !== 0) reject(new Error(stderr.trim() || `Process exited ${code}`))
      else resolve(stdout)
    })
  })
}

analyzeRouter.post('/', upload.single('gpx'), async (req, res) => {
  const name = (req.body.name ?? '').trim()
  const save = req.body.save === 'true'

  if (!name) return void res.status(400).json({ error: 'Run name is required' })
  if (!req.file) return void res.status(400).json({ error: 'No GPX file uploaded' })

  const tmpPath = path.join(os.tmpdir(), `park-run-${Date.now()}.gpx`)
  writeFileSync(tmpPath, req.file.buffer)

  try {
    await run(PYTHON, [path.join(ANALYSIS_DIR, 'download.py'), '--data-dir', DATA_DIR])

    const raw = await run(PYTHON, [
      path.join(ANALYSIS_DIR, 'analyze.py'),
      '--gpx', tmpPath,
      '--data-dir', DATA_DIR,
    ])

    const result: AnalysisResult = JSON.parse(raw)

    if (save) {
      const db = getDb()
      const stmt = db.prepare(`
        INSERT INTO runs (name, total_km, time_str, pace_str, ele_gain, intersected_count, total_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `)
      const info = stmt.run(
        name,
        result.stats.total_km,
        result.stats.time,
        result.stats.pace,
        result.stats.ele_gain,
        result.intersected_count,
        result.total_score,
      )
      const runId = Number(info.lastInsertRowid)
      const runDir = path.join(RUNS_DIR, String(runId))
      mkdirSync(runDir, { recursive: true })
      writeFileSync(path.join(runDir, 'result.json'), JSON.stringify(result))
      return void res.json({ runId, result })
    }

    res.json({ result })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    res.status(500).json({ error: msg })
  } finally {
    rmSync(tmpPath, { force: true })
  }
})
