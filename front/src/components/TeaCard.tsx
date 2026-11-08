import type { ReactNode } from 'react'
import { Link } from 'react-router'
import type { Tea } from '../data/types'
import { offersSummary } from '../hooks/useCatalog'
import { fmtScore, reviewsWord } from '../utils/format'
import { CupIcon } from './Icons'
import { Leaves } from './Leaves'

/** note — строка под карточкой: почему чай здесь (совпавшие ноты, причина совета). */
export function TeaCard({ tea, rank, showShops = true, note }: { tea: Tea; rank?: number; showShops?: boolean; note?: ReactNode }) {
  const { shops, price, perGram } = offersSummary(tea)
  return (
    <Link to={`/teas/${tea.id}`} className="tea-card">
      <span className="tea-art" style={{ background: tea.category.color }}>
        {rank !== undefined && <span className="rank">{rank}</span>}
        <span className="sticker">{fmtScore(tea.stats.avg)}</span>
        <CupIcon size={100} color={tea.category.ink} />
      </span>
      <span className="row between" style={{ gap: 8 }}>
        <span className="small muted" style={{ fontWeight: 600 }}>{tea.category.name}</span>
        <Leaves value={tea.stats.avg} />
      </span>
      <span className="tea-card-name">{tea.title}</span>
      {showShops && (
        <span className="small" style={{ fontWeight: 700 }}>
          {shops}
        </span>
      )}
      <span className="small muted">
        {tea.stats.reviews ? reviewsWord(tea.stats.reviews) : 'Пока без отзывов'}
        {price && ` · ${price}`}
        {perGram && ` · ${perGram}`}
      </span>
      {note && <span className="tea-card-note small">{note}</span>}
    </Link>
  )
}

export function TeaGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid" aria-busy="true" aria-label="Загрузка">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton" style={{ aspectRatio: '3 / 4' }} />
      ))}
    </div>
  )
}
