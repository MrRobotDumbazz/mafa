import { useState, useEffect, useRef } from 'react'
import './App.css'
import { submitVideo, pollJob, USE_MOCK } from './api'
import { hasApiKey, setApiKey } from './apiKey'
import type { JobResult } from './types'
import { getVideoDuration } from './videoUtils'
import { UploadZone } from './components/UploadZone'
import { StatusCard } from './components/StatusCard'
import { VerdictBanner } from './components/VerdictBanner'
import { ViolationCard } from './components/ViolationCard'
import { KeyDialog } from './components/KeyDialog'

type Phase =
  | { kind: 'idle' }
  | { kind: 'uploading'; filename: string; elapsed: number; progress: number }
  | { kind: 'polling'; jobId: string; filename: string; elapsed: number }
  | { kind: 'result'; filename: string; result: JobResult }
  | { kind: 'error'; filename: string; message: string }

const POLL_INTERVAL_MS = 2500
const MAX_POLL_SEC = 310
const MAX_FILE_MB = 200

export default function App() {
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' })
  const [needsKey, setNeedsKey] = useState(!USE_MOCK && !hasApiKey())
  const startRef = useRef<number>(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function clearTimers() {
    if (timerRef.current) clearInterval(timerRef.current)
    if (pollRef.current) clearTimeout(pollRef.current)
  }

  useEffect(() => () => clearTimers(), [])

  function tickElapsed(setter: (e: number) => void) {
    timerRef.current = setInterval(() => {
      setter(Math.floor((Date.now() - startRef.current) / 1000))
    }, 1000)
  }

  function handleKeySave(key: string) {
    setApiKey(key)
    setNeedsKey(false)
  }

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.mov')) {
      setPhase({ kind: 'error', filename: file.name, message: 'Принимаются только файлы формата .mov' })
      return
    }
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      setPhase({
        kind: 'error',
        filename: file.name,
        message: `Файл слишком большой (${(file.size / 1024 / 1024).toFixed(0)} МБ). Максимум — ${MAX_FILE_MB} МБ`,
      })
      return
    }

    clearTimers()
    startRef.current = Date.now()
    setPhase({ kind: 'uploading', filename: file.name, elapsed: 0, progress: 0 })

    const updateElapsed = (e: number) =>
      setPhase((p) =>
        p.kind === 'uploading' || p.kind === 'polling' ? { ...p, elapsed: e } : p,
      )
    tickElapsed(updateElapsed)

    let duration = 60
    try {
      duration = await getVideoDuration(file)
    } catch {
      // fallback
    }

    let jobId: string
    try {
      const res = await submitVideo(file, duration, (pct) => {
        setPhase((p) => (p.kind === 'uploading' ? { ...p, progress: pct } : p))
      })
      jobId = res.job_id
    } catch (e) {
      clearTimers()
      setPhase({ kind: 'error', filename: file.name, message: String(e) })
      return
    }

    setPhase({ kind: 'polling', jobId, filename: file.name, elapsed: 0 })

    const schedulePoll = () => {
      pollRef.current = setTimeout(async () => {
        const elapsed = Math.floor((Date.now() - startRef.current) / 1000)
        if (elapsed > MAX_POLL_SEC) {
          clearTimers()
          setPhase({
            kind: 'error',
            filename: file.name,
            message: 'Превышено время ожидания (5 минут). Попробуйте снова или обратитесь к администратору.',
          })
          return
        }
        try {
          const result = await pollJob(jobId)
          if (result.status === 'processing') {
            schedulePoll()
          } else {
            clearTimers()
            if (result.status === 'failed') {
              setPhase({
                kind: 'error',
                filename: file.name,
                message: result.error ?? 'Сервис не смог обработать видео. Проверьте формат файла.',
              })
            } else {
              setPhase({ kind: 'result', filename: file.name, result })
            }
          }
        } catch (e) {
          clearTimers()
          setPhase({ kind: 'error', filename: file.name, message: String(e) })
        }
      }, POLL_INTERVAL_MS)
    }
    schedulePoll()
  }

  function reset() {
    clearTimers()
    setPhase({ kind: 'idle' })
  }

  const busy = phase.kind === 'uploading' || phase.kind === 'polling'

  return (
    <>
      {needsKey && <KeyDialog onSave={handleKeySave} />}

      <div className="app">
        <header className="header">
          <div className="header__logo" aria-hidden="true">
            <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
              <circle cx="13" cy="11" r="5.5" stroke="white" strokeWidth="2" />
              <circle cx="13" cy="11" r="2" fill="white" />
              <path d="M5 22 Q13 16 21 22" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <p className="header__title">ForteVision</p>
            <p className="header__sub">Система видеоаналитики кассовых операций</p>
          </div>
          <div className="header__right">
            {USE_MOCK && <span className="header__badge">MOCK</span>}
            {!USE_MOCK && (
              <button
                className="header__key-btn"
                onClick={() => setNeedsKey(true)}
                title="Изменить API-ключ"
                aria-label="Изменить API-ключ"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <circle cx="6.5" cy="6.5" r="4" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M10 10l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M6.5 4.5v4M4.5 6.5h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
              </button>
            )}
          </div>
        </header>

        <UploadZone onFile={handleFile} disabled={busy} maxMb={MAX_FILE_MB} />

        {(phase.kind === 'uploading' || phase.kind === 'polling') && (
          <div className="section">
            <StatusCard
              filename={phase.filename}
              elapsed={phase.elapsed}
              phase={phase.kind}
              progress={phase.kind === 'uploading' ? phase.progress : undefined}
            />
          </div>
        )}

        {phase.kind === 'error' && (
          <div className="section">
            <div className="error-card">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true" style={{ flexShrink: 0, marginTop: 1 }}>
                <circle cx="10" cy="10" r="9" stroke="#de3730" strokeWidth="1.5" fill="#fef2f2" />
                <path d="M10 6v5" stroke="#de3730" strokeWidth="2" strokeLinecap="round" />
                <circle cx="10" cy="14" r="1" fill="#de3730" />
              </svg>
              <div>
                <p className="error-card__title">Ошибка обработки</p>
                <p className="error-card__msg">{phase.message}</p>
              </div>
            </div>
            <div style={{ marginTop: 12 }}>
              <button className="btn-reset" onClick={reset}>
                ← Загрузить другое видео
              </button>
            </div>
          </div>
        )}

        {phase.kind === 'result' && (
          <>
            {USE_MOCK && (
              <div className="section">
                <div className="demo-banner" role="alert">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
                    <path d="M10 2l8 14H2L10 2z" fill="#fef3c7" stroke="#d97706" strokeWidth="1.5" strokeLinejoin="round" />
                    <path d="M10 8v4" stroke="#d97706" strokeWidth="2" strokeLinecap="round" />
                    <circle cx="10" cy="14.5" r="1" fill="#d97706" />
                  </svg>
                  <div>
                    <strong className="demo-banner__title">Демо-режим: результат не является анализом видео</strong>
                    <span className="demo-banner__sub">
                      Показаны автоматически сгенерированные данные для демонстрации интерфейса.
                      Таймкоды и кадры взяты из загруженного файла, но нарушения не детектировались.
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div className="section">
              <VerdictBanner verdict={phase.result.verdict} count={phase.result.violations.length} />
            </div>

            {phase.result.violations.length > 0 && (
              <div className="section violations-section">
                <p className="violations-section__heading">
                  Обнаруженные события — {phase.result.violations.length} шт.
                </p>
                <div className="violations-list">
                  {phase.result.violations.map((v, i) => (
                    <ViolationCard key={i} index={i} violation={v} />
                  ))}
                </div>
              </div>
            )}

            <div className="section" style={{ marginTop: 20 }}>
              <button className="btn-reset" onClick={reset}>
                ← Загрузить другое видео
              </button>
            </div>
          </>
        )}

        {USE_MOCK && (
          <p className="mock-notice">Режим разработки: используются мок-данные · backend не подключён</p>
        )}
      </div>
    </>
  )
}
