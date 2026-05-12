import { Router } from 'express'
import { existsSync, readFileSync, rmSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'
import { runDao } from '../dao/runDao.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const RUNS_DIR = path.resolve(__dirname, '../../../runs')

export const runsRouter = Router()

runsRouter.get('/', (_req, res) => {
  res.json(runDao.list())
})

runsRouter.get('/:id', (req, res) => {
  const run = runDao.get(Number(req.params.id))
  if (!run) return void res.status(404).json({ error: 'Not found' })

  const resultPath = path.join(RUNS_DIR, req.params.id, 'result.json')
  if (!existsSync(resultPath)) return void res.status(404).json({ error: 'Result file missing' })

  res.json({ run, result: JSON.parse(readFileSync(resultPath, 'utf-8')) })
})

runsRouter.delete('/:id', (req, res) => {
  runDao.delete(Number(req.params.id))
  rmSync(path.join(RUNS_DIR, req.params.id), { recursive: true, force: true })
  res.json({ ok: true })
})
