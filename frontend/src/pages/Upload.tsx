import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { analyzeRun } from '../api'
import { StatsPanel } from '../components/StatsPanel'
import { RunMap } from '../components/RunMap'
import type { AnalysisResult } from '../types'
import styles from './Upload.module.css'

export function Upload() {
  const navigate = useNavigate()
  const [fileName, setFileName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [name, setName] = useState('')
  const [save, setSave] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<AnalysisResult | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  function onFile(f: File) {
    setFile(f)
    setFileName(f.name)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !name.trim()) return
    setLoading(true)
    setError(null)
    try {
      const { runId, result } = await analyzeRun(name.trim(), file, save)
      if (runId != null) {
        navigate(`/run/${runId}`)
      } else {
        setPreview(result)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  if (preview) {
    return (
      <div className={styles.resultLayout}>
        <StatsPanel name={name} result={preview} />
        <RunMap result={preview} />
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <Link to="/" className={styles.back}>← All Runs</Link>
        <h1 className={styles.title}>Analyze a Run</h1>
        <p className={styles.subtitle}>
          Upload a GPX file to see which public access areas your run crossed.
        </p>

        <form onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="name">Run Name</label>
            <input
              id="name"
              type="text"
              className={styles.input}
              placeholder="e.g. Saturday Morning Park Run"
              value={name}
              onChange={e => setName(e.target.value)}
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel}>GPX File</label>
            <div
              className={`${styles.dropZone} ${dragging ? styles.dragging : ''}`}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={e => {
                e.preventDefault()
                setDragging(false)
                const f = e.dataTransfer.files[0]
                if (f) onFile(f)
              }}
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".gpx"
                className={styles.fileInput}
                onChange={e => { if (e.target.files?.[0]) onFile(e.target.files[0]) }}
              />
              <div className={styles.dropIcon}>📍</div>
              <div className={styles.dropLabel}>Drop your GPX file here</div>
              <div className={styles.dropHint}>or click to browse</div>
              {fileName && <div className={styles.fileName}>{fileName}</div>}
            </div>
          </div>

          <label className={styles.saveRow}>
            <input
              type="checkbox"
              checked={save}
              onChange={e => setSave(e.target.checked)}
            />
            <div>
              <div className={styles.saveTitle}>Save this run</div>
              <div className={styles.saveDesc}>
                Results will be stored on the server and accessible from the home page.
                Uncheck to view results without saving.
              </div>
            </div>
          </label>

          {error && <p className={styles.error}>{error}</p>}

          <button
            type="submit"
            className={styles.submit}
            disabled={!file || !name.trim() || loading}
          >
            {loading ? 'Analyzing…' : 'Analyze Run'}
          </button>
        </form>
      </div>
    </div>
  )
}
