import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import * as api from '../api'
import { useAsync } from '../hooks/useAsync'
import { useCategories, useFlavorWheel } from '../hooks/useCatalog'
import { RecommendationGrid } from '../components/Recommendations'
import { CupIcon, LeafIcon, SearchIcon } from '../components/Icons'
import { ReviewItem } from '../components/ReviewItem'
import { TeaCard, TeaGridSkeleton } from '../components/TeaCard'
import { useAuth } from '../auth/AuthContext'
import { fmtScore, reviewsWord } from '../utils/format'

export function Home() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [q, setQ] = useState('')
  const categories = useCategories()
  const leaders = useAsync(() => api.getCategoryLeaders(), [])
  const top = useAsync(() => api.getTeas({ sort: 'rating' }), [])
  const recent = useAsync(() => api.getRecentReviews(4), [])
  // Советы — только вошедшим и только когда они есть: пустая подсказка на главной не нужна
  const recs = useAsync(() => (user ? api.getRecommendations(4) : Promise.resolve(null)), [user?.id])
  const wheel = useFlavorWheel()
  const feed = useAsync(() => (user ? api.getFeed(4) : Promise.resolve([])), [user?.id])

  function search(e: FormEvent) {
    e.preventDefault()
    navigate(`/teas?q=${encodeURIComponent(q)}`)
  }

  return (
    <div className="page">
      <section className="hero">
        <span className="sticker-float" style={{ left: '6%', top: 40, background: 'var(--surface)', transform: 'rotate(-7deg)' }}>
          честные отзывы
        </span>
        <h1>
          Один чай&nbsp;—<br />
          <span style={{ color: 'var(--accent)' }}>разные чашки</span>
        </h1>
        <p>Сравнивайте чай из разных магазинов. Доверяйте тем, кто пьёт давно. Находите свой.</p>
        <form className="search" role="search" onSubmit={search}>
          <SearchIcon />
          <label htmlFor="home-q" className="sr-only">Поиск чая или магазина</label>
          <input id="home-q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Габа, Да Хун Пао, мёд…" />
          <button className="btn">Найти</button>
        </form>
      </section>

      <section aria-labelledby="cats-h">
        <h2 id="cats-h" className="sr-only">Категории</h2>
        <div className="grid-cats">
          {categories.list.map((c) => (
            <Link key={c.slug} to={`/rankings/categories/${c.slug}`} className="cat-tile" style={{ background: c.color }}>
              <span className="cat-dot" style={{ background: c.ink }}><LeafIcon size={22} /></span>
              <span>
                <span style={{ fontFamily: 'var(--display)', fontSize: 22, display: 'block' }}>{c.plural}</span>
                <span className="small muted" style={{ fontWeight: 600 }}>кто лучше →</span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="diary-band" aria-labelledby="diary-h">
        <span className="cat-dot diary-band-icon" aria-hidden="true"><CupIcon size={54} color="#fff" /></span>
        <div className="stack" style={{ flex: '999 1 360px', gap: 6 }}>
          <h2 id="diary-h">Ведите чайный дневник</h2>
          <p className="muted">Записывайте, что и как заваривали, ставьте оценки и возвращайтесь к любимым чаям.</p>
        </div>
        <Link to={user ? '/diary' : '/register'} className="btn">
          {user ? 'Открыть дневник' : 'Создать аккаунт'}
        </Link>
      </section>

      {recs.data && recs.data.items.length > 0 && (
        <section aria-labelledby="recs-h">
          <div className="section-head">
            <h2 id="recs-h">Вам может понравиться</h2>
            <Link to="/profile">Все советы →</Link>
          </div>
          <RecommendationGrid data={recs.data} index={wheel} limit={4} />
        </section>
      )}

      <section aria-labelledby="leaders-h">
        <div className="section-head">
          <h2 id="leaders-h">Лидеры по видам чая</h2>
          <Link to="/rankings">Все рейтинги →</Link>
        </div>
        {leaders.loading ? (
          <TeaGridSkeleton count={4} />
        ) : (
          <div className="grid">
            {leaders.data?.map(({ category, leader }) => (
              <Link key={category.slug} to={`/rankings/categories/${category.slug}`} className="leader" style={{ background: category.color }}>
                <span className="small" style={{ fontWeight: 700, color: category.ink }}>Лучшие {category.plural.toLowerCase()}</span>
                <span className="leader-name">{leader.shop.title}</span>
                <span className="row" style={{ gap: 8, marginTop: 'auto' }}>
                  <span className="sticker" style={{ transform: 'rotate(-3deg)' }}>{fmtScore(leader.score.avg)}</span>
                  <span className="small" style={{ fontWeight: 600 }}>{reviewsWord(leader.score.reviews)}</span>
                </span>
                <span className="small muted">Хит: {leader.bestTea.title}</span>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="top-h">
        <div className="section-head">
          <h2 id="top-h">Любимцы сообщества</h2>
          <Link to="/teas">Все чаи →</Link>
        </div>
        {top.loading ? (
          <TeaGridSkeleton />
        ) : (
          <div className="grid">
            {top.data?.slice(0, 4).map((t, i) => <TeaCard key={t.id} tea={t} rank={i + 1} />)}
          </div>
        )}
      </section>

      {feed.data && feed.data.length > 0 && (
        <section aria-labelledby="feed-h">
          <div className="section-head">
            <h2 id="feed-h">От тех, на кого вы подписаны</h2>
            <Link to="/profile#following">Подписки →</Link>
          </div>
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
            {feed.data.map((r) => <ReviewItem key={r.id} review={r} showTea />)}
          </div>
        </section>
      )}

      <section aria-labelledby="recent-h">
        <div className="section-head">
          <h2 id="recent-h">Свежие отзывы</h2>
        </div>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
          {recent.data?.map((r) => <ReviewItem key={r.id} review={r} showTea />)}
        </div>
      </section>
    </div>
  )
}
