import { useState } from 'react'
import type { Violation } from '../types'

interface Props {
  index: number
  violation: Violation
}

function fmtTimecode(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = (sec % 60).toFixed(1).padStart(4, '0')
  return `${m}:${s}`
}

export function ViolationCard({ index, violation }: Props) {
  const [activeFrame, setActiveFrame] = useState(0)
  const frame = violation.evidence_frames[activeFrame]

  return (
    <article className="violation-card">
      <header className="violation-card__header">
        <span className="violation-card__num">#{index + 1}</span>
        <h3 className="violation-card__type">{violation.type}</h3>
        <span className="violation-card__timecode">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <circle cx="7" cy="7" r="6" stroke="#64748b" strokeWidth="1.5" />
            <path d="M7 4v3.5l2 2" stroke="#64748b" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          {fmtTimecode(violation.timecode_sec)}
        </span>
      </header>

      <div className="violation-card__body">
        <div className="violation-card__evidence">
          <div className="violation-card__frame-wrap">
            <img
              className="violation-card__frame"
              src={`data:image/jpeg;base64,${frame.image_base64}`}
              alt={`Кадр-доказательство на ${fmtTimecode(frame.timestamp_sec)}`}
            />
            <span className="violation-card__frame-ts">{fmtTimecode(frame.timestamp_sec)}</span>
          </div>

          {violation.evidence_frames.length > 1 && (
            <div className="violation-card__thumbs">
              {violation.evidence_frames.map((f, i) => (
                <button
                  key={i}
                  className={`violation-card__thumb ${i === activeFrame ? 'violation-card__thumb--active' : ''}`}
                  onClick={() => setActiveFrame(i)}
                  aria-label={`Кадр ${i + 1} на ${fmtTimecode(f.timestamp_sec)}`}
                >
                  <img
                    src={`data:image/jpeg;base64,${f.image_base64}`}
                    alt=""
                    aria-hidden="true"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="violation-card__details">
          <section className="violation-card__section">
            <h4 className="violation-card__section-title">Описание</h4>
            <p className="violation-card__description">{violation.description}</p>
          </section>

          <section className="violation-card__section">
            <h4 className="violation-card__section-title">Нормативный источник</h4>
            {violation.normative?.document ? (
              <div className="violation-card__normative">
                <span className="violation-card__normative-doc">{violation.normative.document}</span>
                {violation.normative.clause && (
                  <span className="violation-card__normative-clause">{violation.normative.clause}</span>
                )}
                {violation.normative.url && (
                  <a
                    className="violation-card__normative-link"
                    href={violation.normative.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Открыть источник →
                  </a>
                )}
              </div>
            ) : (
              <p className="violation-card__normative-absent">
                Нормативный источник не указан — ожидается заполнение каталога нарушений
              </p>
            )}
          </section>
        </div>
      </div>
    </article>
  )
}
