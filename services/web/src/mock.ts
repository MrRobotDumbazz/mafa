import type { JobResult } from './types'
import { extractFramesFromFile } from './videoUtils'

interface MockJob {
  file: File
  duration: number
  createdAt: number
}

const jobs = new Map<string, MockJob>()
const done = new Map<string, JobResult>()

export async function mockSubmit(file: File, duration: number): Promise<string> {
  await sleep(300)
  const jobId = 'mock-' + Math.random().toString(36).slice(2, 10)
  jobs.set(jobId, { file, duration, createdAt: Date.now() })
  return jobId
}

export async function mockPollJob(jobId: string): Promise<JobResult> {
  const cached = done.get(jobId)
  if (cached) return cached

  const job = jobs.get(jobId)
  if (!job) throw new Error('Unknown mock job')

  const elapsed = Date.now() - job.createdAt
  if (elapsed < 4000) {
    return { job_id: jobId, status: 'processing', verdict: 'no_violation', violations: [] }
  }

  const result = await buildResult(jobId, job)
  done.set(jobId, result)
  return result
}

async function buildResult(jobId: string, job: MockJob): Promise<JobResult> {
  const dur = job.duration
  // Two timecodes evenly spread, well within video bounds
  const t1 = parseFloat((dur * 0.25).toFixed(1))
  const t2 = parseFloat((dur * 0.65).toFixed(1))
  // Extra frame 1.5 s after first event
  const t1b = parseFloat(Math.min(t1 + 1.5, dur - 0.1).toFixed(1))

  const frames = await extractFramesFromFile(job.file, [t1, t1b, t2])

  const result: JobResult = {
    job_id: jobId,
    status: 'done',
    verdict: 'violation',
    violations: [
      {
        type: 'Работа без перчаток при пересчёте наличных',
        timecode_sec: t1,
        description:
          'Кассир производит пересчёт банкнот без защитных перчаток. Прямой контакт с наличными без средств индивидуальной защиты нарушает требования кассовой дисциплины.',
        evidence_frames: [
          { timestamp_sec: t1, image_base64: frames[0] },
          { timestamp_sec: t1b, image_base64: frames[1] },
        ],
        normative: {
          document: '[Демо] Правила ведения кассовых операций в банках РК',
          clause: 'п. 14',
          url: '',
        },
      },
      {
        type: 'Кассир покинул рабочее место без блокировки кассы',
        timecode_sec: t2,
        description:
          'Кассир отошёл от кассового узла, не заблокировав кассовый ящик. В зоне кассы остались наличные без надзора.',
        evidence_frames: [{ timestamp_sec: t2, image_base64: frames[2] }],
        normative: {
          document: '[Демо] Инструкция по организации кассовой работы',
          clause: 'п. 22',
          url: '',
        },
      },
    ],
  }
  return result
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}
