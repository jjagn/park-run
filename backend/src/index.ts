import express from 'express'
import cors from 'cors'
import { initDb } from './db.js'
import { runsRouter } from './routes/runs.js'
import { analyzeRouter } from './routes/analyze.js'

const app = express()
const PORT = Number(process.env.PORT ?? 3001)

app.use(cors())
app.use(express.json())
app.use('/api/runs', runsRouter)
app.use('/api/analyze', analyzeRouter)

initDb()
app.listen(PORT, () => console.log(`Backend listening on http://localhost:${PORT}`))
