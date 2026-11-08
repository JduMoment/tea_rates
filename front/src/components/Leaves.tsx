import { useState } from 'react'
import { fmtScore } from '../utils/format'

const LEAF = 'M4 20C4 11 10 4 20 4c0 10-7 16-16 16z'

/** Оценка листиками (только отображение). */
export function Leaves({ value, size = 15, color = 'var(--accent)' }: { value: number; size?: number; color?: string }) {
  const full = Math.round(value)
  return (
    <span role="img" aria-label={`Оценка ${fmtScore(value)} из 5`} style={{ display: 'inline-flex', gap: 3 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <svg key={i} width={size} height={size} viewBox="0 0 24 24" fill={i <= full ? color : 'none'} stroke={color} strokeWidth="1.8" aria-hidden="true">
          <path d={LEAF} />
        </svg>
      ))}
    </span>
  )
}

const LABELS = ['', 'Не понравился', 'Так себе', 'Нормально', 'Хороший', 'Восторг']

/** Выбор оценки 1–5 листиками — радиогруппа, работает с клавиатуры. */
export function LeafInput({ value, onChange, name = 'rating' }: { value: number; onChange: (v: number) => void; name?: string }) {
  const [hover, setHover] = useState(0)
  const shown = hover || value
  return (
    <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
      <legend className="field" style={{ marginBottom: 6 }}>Оценка</legend>
      <div className="row" style={{ gap: 4 }} onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map((i) => (
          <label key={i} style={{ cursor: 'pointer', padding: 4 }} onMouseEnter={() => setHover(i)}>
            <input type="radio" name={name} value={i} checked={value === i} onChange={() => onChange(i)} className="sr-only" />
            <span className="sr-only">{i} — {LABELS[i]}</span>
            <svg width="32" height="32" viewBox="0 0 24 24" fill={i <= shown ? 'var(--accent)' : 'none'} stroke="var(--accent)" strokeWidth="1.6" aria-hidden="true">
              <path d={LEAF} />
            </svg>
          </label>
        ))}
        <span className="muted small" style={{ marginLeft: 8, minWidth: 110 }}>{LABELS[shown]}</span>
      </div>
    </fieldset>
  )
}
