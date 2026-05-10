import { useNavigate } from 'react-router-dom'
import type { Run } from '../types'
import { deleteRun } from '../api'
import styles from './RunCard.module.css'

interface Props {
  run: Run
  onDelete: (id: number) => void
}

export function RunCard({ run, onDelete }: Props) {
  const navigate = useNavigate()

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation()
    if (!confirm(`Delete "${run.name}"?`)) return
    await deleteRun(run.id)
    onDelete(run.id)
  }

  return (
    <div className={styles.card} onClick={() => navigate(`/run/${run.id}`)}>
      <div className={styles.header}>
        <span className={styles.name} title={run.name}>{run.name}</span>
        <span className={styles.date}>{run.created_at.slice(0, 10)}</span>
      </div>
      <div className={styles.divider} />
      <div className={styles.stats}>
        <div className={styles.stat}>
          <span className={styles.val}>{run.total_km} km</span>
          <span className={styles.lbl}>Distance</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.val}>{run.time_str}</span>
          <span className={styles.lbl}>Time</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.val}>{run.pace_str}</span>
          <span className={styles.lbl}>Pace</span>
        </div>
      </div>
      <div className={styles.footer}>
        <span className={styles.score}>{run.total_score.toFixed(1)} pts</span>
        <span className={styles.parcels}>
          {run.intersected_count} parcel{run.intersected_count !== 1 ? 's' : ''}
        </span>
        <button className={styles.delete} onClick={handleDelete} title="Delete">✕</button>
      </div>
    </div>
  )
}
