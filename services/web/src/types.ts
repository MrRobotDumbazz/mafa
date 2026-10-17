export interface EvidenceFrame {
  timestamp_sec: number
  image_base64: string
}

export interface ViolationNormative {
  document: string
  clause?: string
  url?: string
}

export interface Violation {
  type: string
  timecode_sec: number
  description: string
  evidence_frames: EvidenceFrame[]
  normative?: ViolationNormative
}

export interface JobCreated {
  job_id: string
  status: 'processing'
}

export interface JobResult {
  job_id: string
  status: 'processing' | 'done' | 'failed'
  verdict: 'no_violation' | 'violation'
  violations: Violation[]
  error?: string
}
