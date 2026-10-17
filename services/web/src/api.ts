import type { JobCreated, JobResult } from './types'
import { mockSubmit, mockPollJob } from './mock'
import { getApiKey } from './apiKey'

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false' && !import.meta.env.VITE_API_URL
const BASE = import.meta.env.VITE_API_URL ?? ''

export { USE_MOCK }

export async function submitVideo(
  file: File,
  duration = 60,
  onProgress?: (pct: number) => void,
): Promise<JobCreated> {
  if (USE_MOCK) {
    const jobId = await mockSubmit(file, duration)
    onProgress?.(100)
    return { job_id: jobId, status: 'processing' }
  }
  const form = new FormData()
  form.append('file', file)
  const data = await xhrUpload(`${BASE}/api/v1/analyze`, form, getApiKey(), onProgress)
  return data as JobCreated
}

export async function pollJob(jobId: string): Promise<JobResult> {
  if (USE_MOCK) {
    return mockPollJob(jobId)
  }
  const res = await fetch(`${BASE}/api/v1/jobs/${jobId}`, {
    headers: { 'X-API-Key': getApiKey() },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Ошибка опроса задания')
  }
  return res.json()
}

function xhrUpload(
  url: string,
  form: FormData,
  apiKey: string,
  onProgress?: (pct: number) => void,
): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', url)
    if (apiKey) xhr.setRequestHeader('X-API-Key', apiKey)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 95))
    }

    xhr.onload = () => {
      onProgress?.(100)
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error('Неверный ответ сервера'))
        }
      } else {
        let detail = xhr.statusText
        try {
          detail = (JSON.parse(xhr.responseText) as { detail?: string }).detail ?? detail
        } catch { /* ignore */ }
        reject(new Error(detail))
      }
    }

    xhr.onerror = () => reject(new Error('Ошибка сети при загрузке'))
    xhr.ontimeout = () => reject(new Error('Превышено время загрузки файла'))
    xhr.timeout = 120_000
    xhr.send(form)
  })
}
