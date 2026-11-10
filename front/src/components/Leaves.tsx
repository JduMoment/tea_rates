import { useState } from 'react'
import { fmtScore } from '../utils/format'

/** Лист как в знаке сайта (лепесток розетки): основание внизу, кончик вверху, прожилка по центру. */
const LEAF = 'M12 22.5C3.6 16.6 3.6 7.4 12 1.5C20.4 7.4 20.4 16.6 12 22.5Z'
const RIB = 'M12 19.5V5'

/** Лист оценки: закрашенный — с прожилкой цвета фона листа, пустой — контур с прожилкой. */
function Leaf({ size, filled, color, strokeWidth }: { size: number; filled: boolean; color: string; strokeWidth: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d={LEAF} fill={filled ? color : 'none'} stroke={color} strokeWidth={strokeWidth} strokeLinejoin="round" />
      <path d={RIB} stroke={filled ? 'rgba(255,255,255,.55)' : color} strokeWidth={strokeWidth * 0.8} strokeLinecap="round" />
    </svg>
  )
}

/** Оценка листиками (только отображение). */
export function Leaves({ value, size = 15, color = 'var(--accent)' }: { value: number; size?: number; color?: string }) {
  const full = Math.round(value)
  return (
    <span role="img" aria-label={`Оценка ${fmtScore(value)} из 5`} style={{ display: 'inline-flex', gap: 3 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <Leaf key={i} size={size} filled={i <= full} color={color} strokeWidth={1.8} />
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
            <Leaf size={32} filled={i <= shown} color="var(--accent)" strokeWidth={1.6} />
          </label>
        ))}
        <span className="muted small" style={{ marginLeft: 8, minWidth: 110 }}>{LABELS[shown]}</span>
      </div>
    </fieldset>
  )
}
