interface Props {
  filename: string
  elapsed: number
  phase: 'uploading' | 'polling'
}

function fmt(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = String(sec % 60).padStart(2, '0')
  return `${m}:${s}`
}

export function StatusCard({ filename, elapsed, phase }: Props) {
  const label = phase === 'uploading' ? 'Загрузка файла…' : 'Анализируется видео…'
  return (
    <div className="status-card">
      <div className="status-card__spinner" aria-hidden="true" />
      <div className="status-card__body">
        <p className="status-card__label">{label}</p>
        <p className="status-card__filename">{filename}</p>
      </div>
      <div className="status-card__timer" aria-live="polite">
        {fmt(elapsed)}
      </div>
    </div>
  )
}
