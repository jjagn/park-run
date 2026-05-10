import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getRuns } from '../api'
import { RunCard } from '../components/RunCard'
import type { Run } from '../types'
import styles from './Home.module.css'

export function Home() {
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getRuns()
      .then(setRuns)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Park Run Analyzer</h1>
        <Link to="/upload" className={styles.btn}>+ Analyze New Run</Link>
      </header>

      {loading && <p className={styles.muted}>Loading…</p>}
      {error && <p className={styles.error}>{error}</p>}

      {!loading && !error && runs.length === 0 && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>📍</div>
          <h2>No runs saved yet</h2>
          <p>Upload a GPX file and check "Save this run" to start building your history.</p>
          <Link to="/upload" className={styles.btn}>Analyze a Run</Link>
        </div>
      )}

      {runs.length > 0 && (
        <div className={styles.grid}>
          {runs.map(run => (
            <RunCard
              key={run.id}
              run={run}
              onDelete={id => setRuns(prev => prev.filter(r => r.id !== id))}
            />
          ))}
        </div>
      )}
    </div>
  )
}
