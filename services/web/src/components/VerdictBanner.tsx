interface Props {
  verdict: 'no_violation' | 'violation'
  count: number
}

export function VerdictBanner({ verdict, count }: Props) {
  if (verdict === 'no_violation') {
    return (
      <div className="verdict-banner verdict-banner--clean" role="status" aria-live="polite">
        <span className="verdict-banner__icon" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="13" stroke="#1a7f37" strokeWidth="2" fill="#dcfce7" />
            <path d="M8 14l4 4 8-8" stroke="#1a7f37" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <div>
          <p className="verdict-banner__title">Нарушение не обнаружено</p>
          <p className="verdict-banner__sub">Видимых признаков нарушений кассовой дисциплины не выявлено</p>
        </div>
      </div>
    )
  }

  return (
    <div className="verdict-banner verdict-banner--violation" role="status" aria-live="polite">
      <span className="verdict-banner__icon" aria-hidden="true">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <path d="M14 2L26 24H2L14 2z" fill="#fef2f2" stroke="#de3730" strokeWidth="2" strokeLinejoin="round" />
          <path d="M14 11v5" stroke="#de3730" strokeWidth="2.5" strokeLinecap="round" />
          <circle cx="14" cy="20" r="1.5" fill="#de3730" />
        </svg>
      </span>
      <div>
        <p className="verdict-banner__title">Обнаружены признаки возможных нарушений</p>
        <p className="verdict-banner__sub">
          {count === 1 ? '1 событие требует проверки' : `${count} события требуют проверки`}
          {' · '}Результат является подсказкой для проверки человеком
        </p>
      </div>
    </div>
  )
}
