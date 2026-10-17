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
          <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
            <rect width="36" height="36" rx="10" fill="#FBE8EE" />
            <circle cx="14" cy="16" r="5" stroke="#9B053F" strokeWidth="2" />
            <path d="M18 20l8 8" stroke="#9B053F" strokeWidth="2.2" strokeLinecap="round" />
            <path d="M22 24l2-2" stroke="#9B053F" strokeWidth="2" strokeLinecap="round" />
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
