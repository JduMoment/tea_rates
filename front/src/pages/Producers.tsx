import { Link } from 'react-router'
import { PageHero } from '../components/PageHero'
import * as api from '../api'
import { useAsync } from '../hooks/useAsync'
import { useCategories } from '../hooks/useCatalog'
import { StoreIcon } from '../components/Icons'
import { Leaves } from '../components/Leaves'
import { TeaGridSkeleton } from '../components/TeaCard'
import { fmtScore, reviewsWord, teasWord } from '../utils/format'

export function Producers() {
  const list = useAsync(() => api.getShops(), [])
  const categories = useCategories()

  return (
    <div className="page" style={{ gap: 32 }}>
      <PageHero
        color="var(--butter)"
        eyebrow="Магазины и чайные дома"
        title="Магазины"
        lead="У каждого — свои сильные стороны. Метки ★ — виды чая, в которых магазин сильнее всего по отзывам."
        stickers={[
          { text: '★ Габы', bg: 'var(--lilac)', style: { right: '9%', top: 52 } },
          { text: '★ Красные', bg: 'var(--peach)', style: { right: '20%', bottom: 52 } },
        ]}
      />
      {list.loading ? (
        <TeaGridSkeleton count={4} />
      ) : (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
          {list.data?.map((p) => (
            <Link key={p.name} to={`/shops/${p.name}`} className="card stack" style={{ textDecoration: 'none', color: 'inherit' }}>
              <div className="row between">
                <span className="row" style={{ gap: 10 }}>
                  <span className="cat-dot" style={{ background: 'var(--accent)' }}><StoreIcon size={20} /></span>
                  <span style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontFamily: 'var(--display)', fontSize: 26, lineHeight: 1.1 }}>{p.title}</span>
                    <span className="small muted">{p.city}{p.founded ? ` · с ${p.founded}` : ''}</span>
                  </span>
                </span>
                <span className="sticker">{fmtScore(p.stats.avg)}</span>
              </div>
              <p className="small" style={{ color: 'var(--ink-2)' }}>{p.description}</p>
              <div className="row" style={{ gap: 6 }}>
                {p.specialties.length ? (
                  p.specialties.map((s) => {
                    const c = categories.byId(s.categoryId)
                    return (
                      c && (
                      <span key={s.categoryId} className="tag" style={{ background: c.color, color: c.ink }}>
                        ★ {c.plural} · {fmtScore(s.avg)}
                      </span>
                      )
                    )
                  })
                ) : (
                  <span className="tag">Пока мало отзывов для выводов</span>
                )}
              </div>
              <div className="row small muted" style={{ marginTop: 'auto' }}>
                <Leaves value={p.stats.avg} />
                {teasWord(p.teaCount)} · {reviewsWord(p.stats.reviews)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
