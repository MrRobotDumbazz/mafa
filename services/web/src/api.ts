import type { JobCreated, JobResult } from './types'
import { mockSubmit, mockPollJob } from './mock'

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false' && !import.meta.env.VITE_API_URL

const BASE = import.meta.env.VITE_API_URL ?? ''
const API_KEY = import.meta.env.VITE_API_KEY ?? 'dev-key'

export { USE_MOCK }

export async function submitVideo(file: File, duration = 60): Promise<JobCreated> {
  if (USE_MOCK) {
    const jobId = await mockSubmit(file, duration)
    return { job_id: jobId, status: 'processing' }
  }
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/api/v1/analyze`, {
    method: 'POST',
    headers: { 'X-API-Key': API_KEY },
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Ошибка загрузки')
  }
  return res.json()
}

export async function pollJob(jobId: string): Promise<JobResult> {
  if (USE_MOCK) {
    return mockPollJob(jobId)
  }
  const res = await fetch(`${BASE}/api/v1/jobs/${jobId}`, {
    headers: { 'X-API-Key': API_KEY },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Ошибка опроса задания')
  }
  return res.json()
}
