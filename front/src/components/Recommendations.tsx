import { Link } from 'react-router'
import type { Recommendations } from '../data/types'
import type { WheelIndex } from '../hooks/useCatalog'
import { plural } from '../utils/format'
import { TeaCard } from './TeaCard'

/** Сетка «Вам может понравиться». Пока у пользователя мало отзывов с нотами — подсказка, как их получить. */
export function RecommendationGrid({ data, index, limit }: { data: Recommendations; index: WheelIndex | undefined; limit?: number }) {
  if (!data.items.length) {
    const left = Math.max(0, data.needed - data.reviews)
    return (
      <div className="empty">
        {left > 0
          ? `Отметьте ноты вкуса ещё в ${left} ${plural(left, 'отзыве', 'отзывах', 'отзывах')} — и здесь появятся чаи, похожие на ваши любимые.`
          : 'Пока не нашли ничего похожего на ваши любимые чаи. Оценивайте ещё — советы станут точнее.'}{' '}
        <Link to="/teas" style={{ fontWeight: 700 }}>Выбрать чай</Link>
      </div>
    )
  }
  return (
    <div className="grid">
      {data.items.slice(0, limit).map(({ tea, reasons }) => (
        <TeaCard
          key={tea.id}
          tea={tea}
          note={index && `Похоже: ${reasons.map((s) => index.flavor(s)?.flavor.title ?? s).join(' · ')}`}
        />
      ))}
    </div>
  )
}
