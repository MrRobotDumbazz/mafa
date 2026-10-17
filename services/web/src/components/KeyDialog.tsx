import { useState, useRef, useEffect } from 'react'

interface Props {
  onSave: (key: string) => void
}

export function KeyDialog({ onSave }: Props) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (value.trim()) onSave(value.trim())
  }

  return (
    <div className="key-dialog-overlay" role="dialog" aria-modal="true" aria-labelledby="key-dialog-title">
      <div className="key-dialog">
        <div className="key-dialog__icon" aria-hidden="true">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <rect width="32" height="32" rx="8" fill="#EBF4FF" />
            <path d="M20 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM12.27 17A7 7 0 0 0 10 23h12a7 7 0 0 0-2.27-6" stroke="#0052CC" strokeWidth="1.8" strokeLinecap="round" />
            <path d="M16 17v2m0 2v.5" stroke="#0052CC" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </div>
        <h2 id="key-dialog-title" className="key-dialog__title">Введите API-ключ</h2>
        <p className="key-dialog__sub">
          Ключ нужен для обращения к backend. Он хранится только в вашем браузере (localStorage)
          и не попадает в код страницы.
        </p>
        <form onSubmit={handleSubmit} className="key-dialog__form">
          <input
            ref={inputRef}
            className="key-dialog__input"
            type="password"
            placeholder="Вставьте ключ…"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoComplete="off"
          />
          <button
            className="key-dialog__btn"
            type="submit"
            disabled={!value.trim()}
          >
            Сохранить и продолжить
          </button>
        </form>
      </div>
    </div>
  )
}
