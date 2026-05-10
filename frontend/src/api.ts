import type { Run, AnalysisResult } from './types'

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(body.error ?? res.statusText)
  }
  return res.json()
}

export const getRuns = (): Promise<Run[]> =>
  fetch('/api/runs').then(r => json(r))

export const getRun = (id: number): Promise<{ run: Run; result: AnalysisResult }> =>
  fetch(`/api/runs/${id}`).then(r => json(r))

export const deleteRun = (id: number): Promise<void> =>
  fetch(`/api/runs/${id}`, { method: 'DELETE' }).then(r => json(r))

export async function analyzeRun(
  name: string,
  gpx: File,
  save: boolean,
): Promise<{ runId?: number; result: AnalysisResult }> {
  const body = new FormData()
  body.append('name', name)
  body.append('gpx', gpx)
  body.append('save', String(save))
  return fetch('/api/analyze', { method: 'POST', body }).then(r => json(r))
}
