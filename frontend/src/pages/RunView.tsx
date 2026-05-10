import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getRun } from '../api'
import { RunMap } from '../components/RunMap'
import { StatsPanel } from '../components/StatsPanel'
import type { AnalysisResult, Run } from '../types'
import styles from './RunView.module.css'


export function RunView() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<Run | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getRun(Number(id))
      .then(({ run, result }) => { setRun(run); setResult(result) })
      .catch(e => setError(e.message))
  }, [id])

  if (error) {
    return (
      <div className={styles.center}>
        <p className={styles.error}>{error}</p>
        <Link to="/" className={styles.back}>← All Runs</Link>
      </div>
    )
  }

  if (!run || !result) {
    return <div className={styles.center}><p className={styles.muted}>Loading…</p></div>
  }

  return (
    <div className={styles.layout}>
      <StatsPanel name={run.name} result={result} backHref="/" />
      <div className={styles.mapArea}>
        <RunMap result={result} />
      </div>
    </div>
  )
}
