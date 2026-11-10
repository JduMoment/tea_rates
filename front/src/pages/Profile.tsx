import { Link, useNavigate } from 'react-router'
import * as api from '../api'
import { useAuth } from '../auth/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { ReviewItem } from '../components/ReviewItem'
import { FlavorProfileView } from '../components/FlavorWheel'
import { RecommendationGrid } from '../components/Recommendations'
import { useFlavorWheel } from '../hooks/useCatalog'
import { Loading } from '../components/Layout'
import { fmtDate, reviewsWord } from '../utils/format'

export function Profile() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const reviews = useAsync(() => api.getUserReviews(user!.id), [user?.id])
  const diary = useAsync(() => api.getDiary(), [user?.id])
  const taste = useAsync(() => api.getUserFlavors(user!.id), [user?.id])
  const recs = useAsync(() => api.getRecommendations(12), [user?.id])
  const wheel = useFlavorWheel()
  const following = useAsync(() => api.getFollowing(), [user?.id])

  if (!user) return null

  return (
    <div className="page">
      <section className="hero hero-page" style={{ background: 'var(--peach)' }}>
        <span className="avatar" style={{ width: 72, height: 72, fontSize: 30, background: 'var(--surface)' }} aria-hidden="true">{user.name.slice(0, 1)}</span>
        <span className="eyebrow">Профиль</span>
        <h1>{user.name}</h1>
        <p>{user.email} · с нами с {fmtDate(user.joined)}</p>
        <div className="row">
          <span className="sticker" style={{ transform: 'rotate(-3deg)' }}>{reviewsWord(reviews.data?.length ?? 0)}</span>
          <Link to="/diary" className="sticker" style={{ background: 'var(--butter)', textDecoration: 'none' }}>
            Дневник: {diary.data?.length ?? 0}
          </Link>
        </div>
      </section>

      <section className="stack" aria-labelledby="taste-h">
        <div className="section-head">
          <h2 id="taste-h">Мой вкус</h2>
          <span className="small muted">По нотам, которые вы отмечали в отзывах</span>
        </div>
        {taste.data && wheel ? (
          <div className="card">
            <FlavorProfileView
              index={wheel}
              profile={taste.data}
              label="Ваш вкусовой профиль по отзывам"
              empty="Отмечайте ноты на колесе, когда пишете отзыв, — и здесь появится ваш вкусовой профиль."
            />
          </div>
        ) : (
          <Loading />
        )}
      </section>

      <section className="stack" aria-labelledby="recs-h">
        <div className="section-head">
          <h2 id="recs-h">Вам может понравиться</h2>
          <span className="small muted">Чаи, которые вы ещё не пробовали, с похожим вкусом</span>
        </div>
        {recs.data ? <RecommendationGrid data={recs.data} index={wheel} /> : <Loading />}
      </section>

      <section className="stack" id="following" aria-labelledby="following-h">
        <div className="section-head">
          <h2 id="following-h">Подписки</h2>
          <span className="small muted">Их новые отзывы — на главной</span>
        </div>
        {following.data?.length ? (
          <div className="row" style={{ gap: 8 }}>
            {following.data.map((u) => (
              <Link key={u.id} to={`/users/${u.id}`} className="chip">
                <span className="avatar" style={{ width: 24, height: 24, fontSize: 12 }} aria-hidden="true">{u.name.slice(0, 1)}</span>
                {u.name}
              </Link>
            ))}
          </div>
        ) : (
          <p className="small muted">Вы пока ни на кого не подписаны. Нажмите на имя автора в отзыве — там есть кнопка «Подписаться».</p>
        )}
      </section>

      <section className="stack">
        <h2>Мои отзывы</h2>
        {reviews.loading && !reviews.data ? (
          <Loading />
        ) : reviews.data?.length ? (
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
            {reviews.data.map((r) => (
              <ReviewItem
                hideExperience
                key={r.id}
                review={r}
                showTea
                onEdit={() => navigate(`/teas/${r.teaId}?edit=${r.id}`)}
                onDelete={async () => {
                  await api.deleteReview(r.id)
                  reviews.reload()
                }}
              />
            ))}
          </div>
        ) : (
          <div className="empty">
            Вы ещё не оставили ни одного отзыва. <Link to="/teas" style={{ fontWeight: 700 }}>Выбрать чай</Link>
          </div>
        )}
      </section>
    </div>
  )
}
