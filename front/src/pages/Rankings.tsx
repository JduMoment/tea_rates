import { Link, NavLink, Navigate, Outlet, useLocation, useParams, useSearchParams } from 'react-router'
import * as api from '../api'
import { Leaves } from '../components/Leaves'
import { Loading } from '../components/Layout'
import { PageHero, type Sticker } from '../components/PageHero'
import { useAuth } from '../auth/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { offersSummary, useCategories } from '../hooks/useCatalog'
import { fmtScore, reviewsWord, teasWord } from '../utils/format'

type Tab = 'categories' | 'shops' | 'teas'

const TABS: { id: Tab; label: string }[] = [
  { id: 'teas', label: 'Топ-20 чаёв' },
  { id: 'categories', label: 'По видам чая' },
  { id: 'shops', label: 'По магазину' },
]

const HERO: Record<Tab, { color: string; title: string; lead: string; stickers: Sticker[] }> = {
  categories: {
    color: 'var(--accent-soft)',
    title: 'Рейтинг по видам чая',
    lead: 'Выберите вид чая — и увидите, в каком магазине он лучше всего. Учитывается число отзывов: одна случайная пятёрка не выведет магазин в лидеры.',
    stickers: [],
  },
  shops: {
    color: 'var(--butter)',
    title: 'Лучшие магазины',
    lead: 'Общая оценка по всем чаям магазина. Рядом — в каких категориях он на первом месте и как оценены остальные.',
    stickers: [
      { text: '№1 в габе', style: { right: '8%', top: 52 } },
      { text: 'общий зачёт', bg: 'var(--peach)', style: { right: '16%', bottom: 56 } },
    ],
  },
  teas: {
    color: 'var(--peach)',
    title: 'Топ-20 чаёв',
    lead: 'Конкретные чаи, которые пользователи оценили выше всего. Отметьте один или несколько видов, чтобы сравнить только их.',
    stickers: [
      { text: '♥ выбор сообщества', style: { right: '9%', top: 56 } },
      { text: 'по отзывам', bg: 'var(--lilac)', style: { right: '18%', bottom: 60 } },
    ],
  },
}

/** Общая шапка и вкладки раздела «Рейтинги». */
export function RankingsLayout() {
  const { pathname } = useLocation()
  const { category } = useParams()
  const tab = (pathname.split('/')[2] as Tab) || 'teas'
  const hero = HERO[tab] ?? HERO.teas
  const categories = useCategories()
  const cat = tab === 'categories' ? categories.bySlug(category) : undefined

  return (
    <div className="page" style={{ gap: 32 }}>
      <PageHero
        color={cat?.color ?? hero.color}
        eyebrow="Рейтинги"
        title={
          cat ? (
            <>
              У кого брать<br />
              <span style={{ color: cat.ink }}>{cat.plural.toLowerCase()}?</span>
            </>
          ) : (
            hero.title
          )
        }
        lead={hero.lead}
        stickers={hero.stickers}
      />
      <nav className="tabs" aria-label="Виды рейтингов">
        {TABS.map((t) => (
          <NavLink key={t.id} to={`/rankings/${t.id}`} className="tab">
            {t.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}

/** Перенаправление со старого адреса: to получает параметры пути и строку запроса. */
export function LegacyRedirect({ to }: { to: (params: Record<string, string | undefined>, search: string) => string }) {
  const params = useParams()
  const { search } = useLocation()
  return <Navigate to={to(params, search)} replace />
}

/** Чипсы видов чая. selected — выбранные; href(id) — куда ведёт клик по чипсу («Все виды» — href('')). */
function CategoryChips({ selected, href, withAll = false }: { selected: string[]; href: (slug: string) => string; withAll?: boolean }) {
  const categories = useCategories()
  return (
    <nav className="toolbar" style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }} aria-label="Категории">
      {withAll && (
        <Link to={href('')} className="chip" aria-pressed={selected.length === 0}>
          Все виды
        </Link>
      )}
      {categories.list.map((c) => (
        <Link key={c.slug} to={href(c.slug)} className="chip" aria-pressed={selected.includes(c.slug)}>
          <span className="dot" style={{ background: c.ink }} aria-hidden="true" />
          {c.plural}
        </Link>
      ))}
    </nav>
  )
}

function Score({ avg, max = 5, color }: { avg: number; max?: number; color?: string }) {
  return (
    <div style={{ flex: '2 1 220px', minWidth: 0 }} className="stack">
      <span className="row" style={{ gap: 10 }}>
        <strong style={{ fontSize: 22 }}>{fmtScore(avg)}</strong>
        <Leaves value={avg} />
      </span>
      <span className="bar" aria-hidden="true">
        <span style={{ width: `${(avg / max) * 100}%`, background: color }} />
      </span>
    </div>
  )
}

// ---------- вкладка «По видам чая» ----------

export function CategoryRanking() {
  const { category } = useParams()
  const { user } = useAuth()
  const categories = useCategories()
  const cat = categories.bySlug(category)
  const rows = useAsync(() => (cat ? api.getCategoryRanking(cat.slug) : Promise.resolve([])), [cat?.slug])

  if (!categories.ready) return <Loading />
  if (!cat) return <Navigate to={`/rankings/categories/${categories.list[0]?.slug ?? ''}`} replace />

  return (
    <>
      <CategoryChips selected={[cat.slug]} href={(slug) => `/rankings/categories/${slug}`} />
      {rows.loading ? (
        <Loading />
      ) : rows.data?.length ? (
        <ol className="stack rank-list">
          {rows.data.map((r, i) => (
            <li key={r.shop.id} className="rank-row" style={i === 0 ? { background: cat.color } : undefined}>
              <span className="rank-num">{i + 1}</span>
              <div style={{ flex: '2 1 240px', minWidth: 0 }} className="stack">
                <Link to={`/shops/${r.shop.name}`} className="rank-name">{r.shop.title}</Link>
                <span className="small muted">{teasWord(r.score.teas)} · {reviewsWord(r.score.reviews)}</span>
              </div>
              <Score avg={r.score.avg} color={cat.ink} />
              <div style={{ flex: '1 1 200px', minWidth: 0 }} className="stack small">
                <span>
                  <span className="muted">Лучший: </span>
                  <Link to={`/teas/${r.bestTea.id}`} style={{ fontWeight: 700 }}>{r.bestTea.title}</Link>
                  {r.bestOffer.priceLabel && <span className="muted"> · {r.bestOffer.priceLabel}</span>}
                </span>
                <a href={r.bestOffer.url ?? r.shop.site} target="_blank" rel="noreferrer" style={{ fontWeight: 700 }}>Купить ↗</a>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <div className="empty">В этой категории пока нет чаёв.</div>
      )}
      {user && (
        <div>
          <Link to={`/teas/new?category=${cat.slug}`} className="btn btn-ghost">+ Добавить {cat.name.toLowerCase()}</Link>
        </div>
      )}
    </>
  )
}

// ---------- вкладка «Производители» ----------

export function ProducerRanking() {
  const rows = useAsync(() => api.getShopRanking(), [])
  const categories = useCategories()

  if (rows.loading) return <Loading />
  if (!rows.data?.length) return <div className="empty">Магазинов пока нет.</div>

  return (
    <ol className="stack rank-list">
      {rows.data.map(({ shop: p, leads, scores }, i) => (
        <li key={p.name} className="rank-row" style={i === 0 ? { background: 'var(--butter)' } : undefined}>
          <span className="rank-num">{i + 1}</span>
          <div style={{ flex: '2 1 240px', minWidth: 0 }} className="stack">
            <Link to={`/shops/${p.name}`} className="rank-name">{p.title}</Link>
            <span className="small muted">{p.city}, {p.country} · {teasWord(p.teaCount)} · {reviewsWord(p.stats.reviews)}</span>
            {leads.length > 0 && (
              <span className="row" style={{ gap: 6 }}>
                {leads.map((id) => {
                  const c = categories.byId(id)
                  if (!c) return null
                  return (
                    <Link key={id} to={`/rankings/categories/${c.slug}`} className="sticker" style={{ fontSize: 12, background: c.color, textDecoration: 'none' }}>
                      №1 · {c.plural.toLowerCase()}
                    </Link>
                  )
                })}
              </span>
            )}
          </div>
          <Score avg={p.stats.avg} />
          <div style={{ flex: '1 1 220px', minWidth: 0 }} className="row" aria-label="Оценки по категориям">
            {scores.map((s) => {
              const c = categories.byId(s.categoryId)
              if (!c) return null
              return (
                <Link key={s.categoryId} to={`/rankings/categories/${c.slug}`} className="tag" style={{ background: c.color, color: c.ink, textDecoration: 'none' }}>
                  {c.name} {fmtScore(s.avg)}
                </Link>
              )
            })}
          </div>
        </li>
      ))}
    </ol>
  )
}

// ---------- вкладка «Топ-20 чаёв» ----------

export function TeaRanking() {
  const [params] = useSearchParams()
  const categories = useCategories()
  // ?category=gaba,red — несколько видов через запятую; неизвестные отбрасываются
  const selected = (params.get('category') ?? '').split(',').filter((slug) => categories.bySlug(slug))
  const key = selected.join(',')
  const rows = useAsync(
    () => (categories.ready ? api.getTopTeas({ categories: selected }) : Promise.resolve([])),
    [key, categories.ready],
  )

  // Клик по чипсу добавляет вид в выбор или убирает его оттуда
  const href = (slug: string) => {
    const next = !slug ? [] : selected.includes(slug) ? selected.filter((x) => x !== slug) : [...selected, slug]
    const ordered = categories.list.map((c) => c.slug).filter((c) => next.includes(c))
    return ordered.length ? `/rankings/teas?category=${ordered.join(',')}` : '/rankings/teas'
  }

  return (
    <>
      <CategoryChips withAll selected={selected} href={href} />
      {rows.loading || !categories.ready ? (
        <Loading />
      ) : rows.data?.length ? (
        <ol className="stack rank-list">
          {rows.data.map((t, i) => (
            <li key={t.id} className="rank-row" style={i < 3 ? { background: t.category.color } : undefined}>
              <span className="rank-num">{i + 1}</span>
              <div style={{ flex: '2 1 240px', minWidth: 0 }} className="stack">
                <Link to={`/teas/${t.id}`} className="rank-name">{t.title}</Link>
                {/* Оценка — по всем магазинам, поэтому без названия магазина: только их число и цена «от» */}
                <span className="small muted">
                  {[offersSummary(t).count, t.region, offersSummary(t).price].filter(Boolean).join(' · ')}
                </span>
              </div>
              <Score avg={t.stats.avg} color={t.category.ink} />
              <div style={{ flex: '1 1 160px', minWidth: 0 }} className="stack small">
                <span className="tag" style={{ alignSelf: 'flex-start', background: i < 3 ? 'var(--surface)' : t.category.color, color: t.category.ink }}>
                  {t.category.name}
                </span>
                <span className="muted">{reviewsWord(t.stats.reviews)}</span>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <div className="empty">Пока никто не оценил чаи выбранных видов.</div>
      )}
    </>
  )
}
