import { useRef, useState, DragEvent, ChangeEvent } from 'react'

interface Props {
  onFile: (file: File) => void
  disabled?: boolean
  maxMb?: number
}

export function UploadZone({ onFile, disabled, maxMb }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) onFile(file)
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) onFile(file)
    e.target.value = ''
  }

  return (
    <div
      className={`upload-zone ${dragging ? 'upload-zone--drag' : ''} ${disabled ? 'upload-zone--disabled' : ''}`}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && !disabled && inputRef.current?.click()}
      aria-label="Загрузить видеофайл"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".mov,video/quicktime"
        style={{ display: 'none' }}
        onChange={handleChange}
        disabled={disabled}
      />
      <div className="upload-zone__icon">
        <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
          <rect width="52" height="52" rx="14" fill="#FBE8EE" />
          <path d="M26 15v16M26 15l-6 6M26 15l6 6" stroke="#9B053F" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M15 35v2a2 2 0 002 2h18a2 2 0 002-2v-2" stroke="#9B053F" strokeWidth="2.5" strokeLinecap="round"/>
        </svg>
      </div>
      <p className="upload-zone__title">Перетащите видеофайл или нажмите для выбора</p>
      <p className="upload-zone__hint">Формат .mov · до {maxMb ?? 200} МБ</p>
    </div>
  )
}
