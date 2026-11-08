import type { CSSProperties, ReactNode } from 'react'

export interface Sticker {
  text: ReactNode
  bg?: string
  /** позиция в процентах/px от краёв плашки */
  style: CSSProperties
  rotate?: number
}

/**
 * Цветная шапка страницы — тот же приём, что hero на главной:
 * скруглённая плашка, Yeseva-заголовок, наклейки под углом.
 */
export function PageHero({
  title,
  eyebrow,
  lead,
  color = 'var(--accent-soft)',
  stickers = [],
  center = false,
  children,
}: {
  title: ReactNode
  eyebrow?: ReactNode
  lead?: ReactNode
  color?: string
  stickers?: Sticker[]
  center?: boolean
  children?: ReactNode
}) {
  return (
    <section className={`hero hero-page${center ? ' center' : ''}`} style={{ background: color }}>
      {stickers.map((s, i) => (
        <span
          key={i}
          className="sticker-float"
          aria-hidden="true"
          style={{ background: s.bg ?? 'var(--surface)', transform: `rotate(${s.rotate ?? (i % 2 ? 6 : -5)}deg)`, ...s.style }}
        >
          {s.text}
        </span>
      ))}
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h1>{title}</h1>
      {lead && <p>{lead}</p>}
      {children}
    </section>
  )
}
