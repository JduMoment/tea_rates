import { useState } from 'react'
import { Link } from 'react-router'
import * as api from '../api'
import { useAuth } from '../auth/AuthContext'
import type { Photo, Review } from '../data/types'
import { useFlavorWheel } from '../hooks/useCatalog'
import { experienceLine, fmtDate } from '../utils/format'
import { FlavorTags } from './FlavorWheel'
import { infusionText } from '../utils/infusion'
import { Leaves } from './Leaves'

/** hideExperience — на странице автора: там все отзывы его, а опыт показан в шапке. */
export function ReviewItem({
  review,
  showTea = false,
  hideExperience = false,
  onEdit,
  onDelete,
}: {
  review: Review
  showTea?: boolean
  hideExperience?: boolean
  onEdit?: () => void
  onDelete?: () => void
}) {
  const wheel = useFlavorWheel()
  const infusion = infusionText(review)
  const [photo, setPhoto] = useState<Photo | null>(null)
  return (
    <article className="review">
      <div className="row between">
        <div className="row" style={{ gap: 10 }}>
          <span className="avatar" aria-hidden="true">{review.user.name.slice(0, 1)}</span>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <Link to={`/users/${review.user.id}`} className="review-author">{review.user.name}</Link>
            {review.user.experience && !hideExperience && (
              <span className="small muted" title="Сколько разных чаёв, видов чая и магазинов автор оценил на сайте">
                {experienceLine(review.user.experience)}
              </span>
            )}
            <span className="small muted">
              {fmtDate(review.createdAt)}
              {review.editedAt && <span title={`Изменён ${fmtDate(review.editedAt)}`}> · изменён</span>}
            </span>
          </div>
        </div>
        <Leaves value={review.rating} size={17} />
      </div>
      <p className="small">
        {showTea && review.tea && (
          <>
            <Link to={`/teas/${review.tea.id}`} style={{ fontWeight: 700 }}>{review.tea.title}</Link>
            <span className="muted"> · </span>
          </>
        )}
        <span className="muted">куплен в </span>
        <Link to={`/shops/${review.shop.name}`} style={{ fontWeight: 700 }}>{review.shop.title}</Link>
        {/* Покупка: цена и партия, если автор их указал */}
        {[review.priceLabel, review.harvest.toLowerCase()].filter(Boolean).map((x) => (
          <span key={x} className="muted"> · {x}</span>
        ))}
      </p>
      <p>{review.text}</p>
      {review.photos.length > 0 && (
        <div className="review-photos">
          {review.photos.map((p) => (
            <button key={p.id} type="button" className="review-photo" onClick={() => setPhoto(p)} aria-label="Открыть фото">
              <img src={p.thumbUrl} alt="" loading="lazy" width={p.width} height={p.height} />
            </button>
          ))}
        </div>
      )}
      {wheel && review.tastes.length > 0 && (
        <p className="small muted" style={{ margin: 0 }}>
          Вкус: {review.tastes.map((t) => wheel.taste(t)?.title.toLowerCase()).filter(Boolean).join(', ')}
        </p>
      )}
      {infusion && <p className="small muted" style={{ margin: 0 }}>Настой: {infusion}</p>}
      <div className="row between">
        <FlavorTags index={wheel} slugs={review.flavors} />
        <div className="row" style={{ gap: 6, marginLeft: 'auto' }}>
          <HelpfulButton review={review} />
          {onEdit && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={onEdit}>Изменить</button>
          )}
          {onDelete && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={onDelete}>Удалить</button>
          )}
        </div>
      </div>
      {photo && <Lightbox photo={photo} onClose={() => setPhoto(null)} />}
    </article>
  )
}

/** «Полезно · 3». Гостю и автору — только число (если оно есть), без кнопки. */
function HelpfulButton({ review }: { review: Review }) {
  const { user } = useAuth()
  const [state, setState] = useState({ helpful: review.helpful, voted: review.voted })
  const [busy, setBusy] = useState(false)
  const canVote = user && user.id !== review.user.id

  if (!canVote) {
    return state.helpful > 0 ? <span className="small muted">Полезно · {state.helpful}</span> : null
  }
  return (
    <button
      type="button"
      className="chip chip-sm"
      aria-pressed={state.voted}
      disabled={busy}
      title={state.voted ? 'Убрать отметку' : 'Отметить отзыв полезным'}
      onClick={async () => {
        setBusy(true)
        try {
          const r = await api.voteReview(review.id, !state.voted)
          setState({ helpful: r.helpful, voted: r.voted })
        } finally {
          setBusy(false)
        }
      }}
    >
      👍 Полезно{state.helpful > 0 && ` · ${state.helpful}`}
    </button>
  )
}

function Lightbox({ photo, onClose }: { photo: Photo; onClose: () => void }) {
  return (
    <div className="lightbox" role="dialog" aria-modal="true" aria-label="Фото к отзыву" onClick={onClose} onKeyDown={(e) => e.key === 'Escape' && onClose()}>
      <img src={photo.url} alt="" width={photo.width} height={photo.height} />
      <button type="button" className="btn btn-light btn-sm lightbox-close" autoFocus onClick={onClose}>Закрыть ✕</button>
    </div>
  )
}
