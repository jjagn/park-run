import { DatabaseSync } from 'node:sqlite'
import { mkdirSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.resolve(__dirname, '../../data')
const DB_PATH = path.join(DATA_DIR, 'runs.db')

let _db: DatabaseSync | null = null

export function getDb(): DatabaseSync {
  if (!_db) {
    mkdirSync(DATA_DIR, { recursive: true })
    _db = new DatabaseSync(DB_PATH)
    _db.exec('PRAGMA journal_mode=WAL')
  }
  return _db
}

export function initDb(): void {
  getDb().exec(`
    CREATE TABLE IF NOT EXISTS runs (
      id                INTEGER PRIMARY KEY AUTOINCREMENT,
      name              TEXT    NOT NULL,
      created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
      total_km          REAL,
      time_str          TEXT,
      pace_str          TEXT,
      ele_gain          REAL,
      intersected_count INTEGER,
      total_score       REAL
    )
  `)
}
