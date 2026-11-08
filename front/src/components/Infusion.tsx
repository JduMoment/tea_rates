import type { InfusionStats } from '../data/types'
import { SCALES, type InfusionValue } from '../utils/infusion'

/** Ввод в форме отзыва: пять кнопок на шкалу, повторный клик снимает отметку. */
export function InfusionInput({ value, onChange }: { value: InfusionValue; onChange: (v: InfusionValue) => void }) {
  return (
    <fieldset className="stack infusion-input" style={{ gap: 10 }}>
      <legend className="field" style={{ display: 'block' }}>
        Настой <span className="muted" style={{ fontWeight: 500 }}>· необязательно</span>
      </legend>
      {SCALES.map((s) => (
        <div key={s.key} className="infusion-row">
          <span className="small" style={{ fontWeight: 700 }}>{s.title}</span>
          <div className="infusion-scale" role="radiogroup" aria-label={s.title}>
            <span className="small muted">{s.low}</span>
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                role="radio"
                aria-checked={value[s.key] === n}
                aria-label={`${s.title}: ${n} из 5`}
                className="infusion-dot"
                onClick={() => onChange({ ...value, [s.key]: value[s.key] === n ? null : n })}
              >
                {n}
              </button>
            ))}
            <span className="small muted">{s.high}</span>
          </div>
        </div>
      ))}
    </fieldset>
  )
}

const fmt = (v: number) => v.toFixed(1).replace('.', ',')

/** Средние по отзывам: точка на шкале от «лёгкое» до «плотное». */
export function InfusionBars({ stats }: { stats: InfusionStats }) {
  if (!stats.reviews) return null
  return (
    <div className="stack" style={{ gap: 12 }}>
      <h3 style={{ fontSize: 22 }}>Настой</h3>
      <p className="small muted" style={{ margin: 0 }}>
        По {stats.reviews} {stats.reviews === 1 ? 'отзыву' : 'отзывам'}, где оценили настой, — от 1 до 5.
      </p>
      {SCALES.map((s) => {
        const v = stats[s.key]
        return (
          <div key={s.key} className="stack" style={{ gap: 4 }}>
            <span className="row between small">
              <strong>{s.title}</strong>
              <span className="muted">{v == null ? '—' : fmt(v)}</span>
            </span>
            <span className="meter" aria-hidden="true">
              {v != null && <span className="meter-mark" style={{ left: `${((v - 1) / 4) * 100}%` }} />}
            </span>
            <span className="row between small muted">
              <span>{s.low}</span>
              <span>{s.high}</span>
            </span>
          </div>
        )
      })}
    </div>
  )
}
