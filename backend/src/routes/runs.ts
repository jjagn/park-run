import { Router } from 'express'
import { existsSync, readFileSync, rmSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'
import { getDb } from '../db.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const RUNS_DIR = path.resolve(__dirname, '../../../runs')

export const runsRouter = Router()

runsRouter.get('/', (_req, res) => {
  const runs = getDb().prepare('SELECT * FROM runs ORDER BY created_at DESC').all()
  res.json(runs)
})

runsRouter.get('/:id', (req, res) => {
  const run = getDb().prepare('SELECT * FROM runs WHERE id = ?').get(req.params.id)
  if (!run) return void res.status(404).json({ error: 'Not found' })

  const resultPath = path.join(RUNS_DIR, req.params.id, 'result.json')
  if (!existsSync(resultPath)) return void res.status(404).json({ error: 'Result file missing' })

  res.json({ run, result: JSON.parse(readFileSync(resultPath, 'utf-8')) })
})

runsRouter.delete('/:id', (req, res) => {
  getDb().prepare('DELETE FROM runs WHERE id = ?').run(req.params.id)
  rmSync(path.join(RUNS_DIR, req.params.id), { recursive: true, force: true })
  res.json({ ok: true })
})
