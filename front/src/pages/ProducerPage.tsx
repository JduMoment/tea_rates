import { Link, useParams } from 'react-router'
import * as api from '../api'
import { useAuth } from '../auth/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { usePageTitle } from '../hooks/usePageTitle'
import { useCategories } from '../hooks/useCatalog'
import { Leaves } from '../components/Leaves'
import { Loading, NotFoundBlock } from '../components/Layout'
import { TeaCard } from '../components/TeaCard'
import { ImageUpload, ShopLogo } from '../components/CatalogImage'
import { fmtScore, reviewsWord, teasWord } from '../utils/format'

export function ProducerPage() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const categories = useCategories()
  const res = useAsync(() => api.getShop(id), [id])
  usePageTitle(res.data?.title)

  if (res.loading && !res.data) return <Loading />
  const p = res.data
  if (!p) return <NotFoundBlock text="Магазин не найден" />

  const famous = p.specialties.flatMap((s) => categories.byId(s.categoryId)?.instrumental ?? [])
  const addHref = `/teas/new?shop=${p.name}`

  return (
    <div className="page">
      <nav className="small muted" aria-label="Навигация">
        <Link to="/shops">Магазины</Link> / {p.title}
      </nav>

      <section className="hero hero-page">
        {p.specialties.slice(0, 2).map((s, i) => {
          const c = categories.byId(s.categoryId)
          if (!c) return null
          return (
            <span key={s.categoryId} className="sticker-float" aria-hidden="true" style={{ background: c.color, right: i ? '18%' : '7%', top: i ? 'auto' : 52, bottom: i ? 56 : 'auto', transform: `rotate(${i ? -5 : 6}deg)` }}>
              ★ {c.plural} · {fmtScore(s.avg)}
            </span>
          )
        })}
        <span className="eyebrow">{p.city}, {p.country}{p.founded ? ` · с ${p.founded} года` : ''}</span>
        <div className="row" style={{ gap: 18, flexWrap: 'nowrap' }}>
          {p.logoUrl && <ShopLogo shop={p} size={72} />}
          <h1>{p.title}</h1>
        </div>
        {famous.length > 0 && (
          <p style={{ fontFamily: 'var(--display)', fontSize: 26, color: 'var(--ink)', maxWidth: 720 }}>
            Славится {famous.join(' и ')}
          </p>
        )}
        <p>{p.description}</p>
        <div className="row">
          <span className="sticker" style={{ fontSize: 20 }}>{fmtScore(p.stats.avg)}</span>
          <Leaves value={p.stats.avg} size={20} />
          <span className="small" style={{ fontWeight: 600 }}>{teasWord(p.teaCount)} · {reviewsWord(p.stats.reviews)}</span>
          <span className="small muted">с учётом опыта авторов</span>
        </div>
        <div className="row">
          <a href={p.site} target="_blank" rel="noreferrer" className="btn">Сайт магазина ↗</a>
          {user && <Link to={addHref} className="btn btn-ghost">+ Добавить чай этого магазина</Link>}
        </div>
        {user && !p.logoUrl && (
          <ImageUpload label="Загрузить логотип" upload={(f) => api.uploadShopLogo(p.id, f)} onDone={res.reload} />
        )}
      </section>

      <section aria-labelledby="matrix-h">
        <div className="section-head">
          <h2 id="matrix-h">Оценки по категориям</h2>
          <span className="small muted">Средняя оценка чаёв категории в этом магазине, с учётом опыта авторов</span>
        </div>
        <div className="matrix">
          {p.scores.map((s) => {
            const c = categories.byId(s.categoryId)
            if (!c) return null
            const star = p.specialties.some((x) => x.categoryId === s.categoryId)
            return (
              <Link key={s.categoryId} to={`/teas?${new URLSearchParams({ shop: p.name, category: c.slug })}`} className="matrix-cell" style={{ background: c.color, textDecoration: 'none' }}>
                <span className="row between">
                  <span style={{ fontWeight: 700, color: c.ink }}>{c.plural}</span>
                  {star && <span className="sticker" style={{ fontSize: 12 }}>★ фирменное</span>}
                </span>
                <span className="score-big">{fmtScore(s.avg)}</span>
                <span className="bar" aria-hidden="true"><span style={{ width: `${(s.avg / 5) * 100}%`, background: c.ink }} /></span>
                <span className="small muted">{teasWord(s.teas)} · {reviewsWord(s.reviews)}</span>
              </Link>
            )
          })}
        </div>
      </section>

      <section aria-labelledby="teas-h">
        <div className="section-head">
          <h2 id="teas-h">Чаи {p.title}</h2>
          <Link to={`/teas?shop=${p.name}`}>Открыть в каталоге →</Link>
        </div>
        <div className="grid">
          {p.teas.map((t) => <TeaCard key={t.id} tea={t} showShops={false} />)}
        </div>
      </section>
    </div>
  )
}
