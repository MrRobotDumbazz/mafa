interface Props {
  filename: string
  elapsed: number
  phase: 'uploading' | 'polling'
  progress?: number
}

function fmt(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = String(sec % 60).padStart(2, '0')
  return `${m}:${s}`
}

export function StatusCard({ filename, elapsed, phase, progress }: Props) {
  const label = phase === 'uploading' ? 'Загрузка файла…' : 'Анализируется видео…'
  const showProgress = phase === 'uploading' && progress !== undefined && progress > 0

  return (
    <div className="status-card">
      <div className="status-card__spinner" aria-hidden="true" />
      <div className="status-card__body">
        <p className="status-card__label">{label}</p>
        <p className="status-card__filename">{filename}</p>
        {showProgress && (
          <div className="upload-progress" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
            <div className="upload-progress__bar" style={{ width: `${progress}%` }} />
            <span className="upload-progress__pct">{progress}%</span>
          </div>
        )}
      </div>
      <div className="status-card__timer" aria-live="polite">
        {fmt(elapsed)}
      </div>
    </div>
  )
}
