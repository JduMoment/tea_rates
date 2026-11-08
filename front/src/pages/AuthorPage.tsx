import { useState } from 'react'
import { Link, Navigate, useParams } from 'react-router'
import * as api from '../api'
import { useAuth } from '../auth/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { useFlavorWheel } from '../hooks/useCatalog'
import { FlavorProfileView } from '../components/FlavorWheel'
import { Loading, NotFoundBlock } from '../components/Layout'
import { ReviewItem } from '../components/ReviewItem'
import type { Author } from '../data/types'
import { fmtDate, plural, reviewsWord, teasWord } from '../utils/format'

/** Публичный профиль автора: его отзывы и вкус, подписка. Дневник — личный, здесь его нет. */
export function AuthorPage() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const author = useAsync(() => api.getAuthor(id), [id, user?.id])
  const reviews = useAsync(() => api.getUserReviews(Number(id)), [id])
  const taste = useAsync(() => api.getUserFlavors(Number(id)), [id])
  const wheel = useFlavorWheel()

  if (user && String(user.id) === id) return <Navigate to="/profile" replace />
  if (author.loading && !author.data) return <Loading />
  const a = author.data
  if (!a) return <NotFoundBlock text="Такого автора нет" />

  return (
    <div className="page">
      <section className="hero hero-page" style={{ background: 'var(--butter)' }}>
        <span className="avatar" style={{ width: 72, height: 72, fontSize: 30, background: 'var(--surface)' }} aria-hidden="true">{a.name.slice(0, 1)}</span>
        <span className="eyebrow">Автор отзывов</span>
        <h1>{a.name}</h1>
        <p>С нами с {fmtDate(a.joined)} · {reviewsWord(a.reviews)} · попробовал(а) {teasWord(a.teas)}</p>
        <div className="row">
          <span className="sticker" style={{ transform: 'rotate(-3deg)' }}>
            {a.followers} {plural(a.followers, 'подписчик', 'подписчика', 'подписчиков')}
          </span>
          <FollowButton author={a} onChanged={author.reload} />
        </div>
      </section>

      <section className="stack" aria-labelledby="a-taste-h">
        <h2 id="a-taste-h">Вкус автора</h2>
        {taste.data && wheel ? (
          <div className="card">
            <FlavorProfileView index={wheel} profile={taste.data} label={`Вкусовой профиль: ${a.name}`} empty="Автор пока не отмечал ноты вкуса в отзывах." />
          </div>
        ) : (
          <Loading />
        )}
      </section>

      <section className="stack" aria-labelledby="a-reviews-h">
        <h2 id="a-reviews-h">Отзывы</h2>
        {reviews.data?.length ? (
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
            {reviews.data.map((r) => <ReviewItem key={r.id} review={r} showTea />)}
          </div>
        ) : reviews.loading ? (
          <Loading />
        ) : (
          <div className="empty">Отзывов пока нет.</div>
        )}
      </section>
    </div>
  )
}

function FollowButton({ author, onChanged }: { author: Author; onChanged: () => void }) {
  const { user } = useAuth()
  const [busy, setBusy] = useState(false)
  if (!user) {
    return <Link to="/login" state={{ from: `/users/${author.id}` }} className="btn">Подписаться</Link>
  }
  return (
    <button
      type="button"
      className={author.followedByMe ? 'btn btn-ghost' : 'btn'}
      disabled={busy}
      onClick={async () => {
        setBusy(true)
        try {
          await api.followAuthor(author.id, !author.followedByMe)
          onChanged()
        } finally {
          setBusy(false)
        }
      }}
    >
      {author.followedByMe ? 'Вы подписаны ✓' : 'Подписаться'}
    </button>
  )
}
