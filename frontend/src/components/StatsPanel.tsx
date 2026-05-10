import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { Link } from 'react-router-dom'
import type { AnalysisResult } from '../types'
import styles from './StatsPanel.module.css'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Title, Tooltip)

const GRID = '#3c3836'
const TICK = '#a89984'

function chartOpts(yLabel: string, reverse = false): object {
  return {
    responsive: true,
    animation: false,
    plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
    elements: { point: { radius: 0 } },
    scales: {
      x: { ticks: { color: TICK, maxTicksLimit: 5 }, grid: { color: GRID },
           title: { display: true, text: 'km', color: TICK } },
      y: { reverse, ticks: { color: TICK }, grid: { color: GRID },
           title: { display: true, text: yLabel, color: TICK } },
    },
  }
}

interface Props {
  name: string
  result: AnalysisResult
  backHref?: string
}

export function StatsPanel({ name, result, backHref }: Props) {
  const { stats, total_score, intersected_count } = result

  const eleData = {
    labels: stats.chart_dist,
    datasets: [{
      data: stats.chart_ele,
      borderColor: '#83a598',
      backgroundColor: 'rgba(131,165,152,0.15)',
      fill: true, tension: 0.3, borderWidth: 1.5,
    }],
  }

  const paceData = {
    labels: stats.chart_dist,
    datasets: [{
      data: stats.chart_pace,
      borderColor: '#b8bb26',
      backgroundColor: 'rgba(184,187,38,0.15)',
      fill: true, tension: 0.3, borderWidth: 1.5,
    }],
  }

  return (
    <aside className={styles.panel}>
      {backHref && (
        <Link to={backHref} className={styles.menuBtn} title="All Runs">
          <span className={styles.hamburger} />
          <span className={styles.hamburger} />
          <span className={styles.hamburger} />
        </Link>
      )}
      <h2 className={styles.title}>{name}</h2>

      <h3 className={styles.section}>Score</h3>
      <div className={styles.row}>
        <span className={styles.label}>Total Points</span>
        <span className={`${styles.value} ${styles.score}`}>{total_score.toFixed(1)}</span>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Parcels Hit</span>
        <span className={styles.value}>{intersected_count}</span>
      </div>

      <h3 className={styles.section}>Summary</h3>
      <div className={styles.row}>
        <span className={styles.label}>Distance</span>
        <span className={styles.value}>{stats.total_km} km</span>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Time</span>
        <span className={styles.value}>{stats.time}</span>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Avg Pace</span>
        <span className={styles.value}>{stats.pace}</span>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Elevation Gain</span>
        <span className={styles.value}>{stats.ele_gain} m</span>
      </div>
      {stats.ele_min != null && (
        <div className={styles.row}>
          <span className={styles.label}>Min / Max Ele</span>
          <span className={styles.value}>{stats.ele_min} / {stats.ele_max} m</span>
        </div>
      )}

      <h3 className={styles.section}>Elevation</h3>
      <Line data={eleData} options={chartOpts('m') as never} />

      <h3 className={styles.section}>Pace</h3>
      <Line data={paceData} options={chartOpts('min/km', true) as never} />

      <div className={styles.legend}>
        <div className={styles.legendTitle}>Land Access</div>
        <div className={styles.legendRow}>
          <span className={styles.swatch} style={{ background: '#8ec07c', borderColor: '#689d6a' }} />
          Track passed through
        </div>
        <div className={styles.legendRow}>
          <span className={styles.swatch} style={{ background: '#fe8019', borderColor: '#d65d0e' }} />
          Buffer only
        </div>
        <div className={styles.legendNote}>Points: 20–100 (smaller = more)</div>
      </div>
    </aside>
  )
}
