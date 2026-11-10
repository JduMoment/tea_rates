import { useState } from 'react'
import { Link } from 'react-router'
import * as api from '../api'
import type { RatedOffer, Review, TeaDetails } from '../data/types'
import { useAsync } from '../hooks/useAsync'
import type { WheelIndex } from '../hooks/useCatalog'
import { fmtPerGram, fmtScore, reviewsWord } from '../utils/format'
import { FlavorWheel } from './FlavorWheel'
import { textOn } from '../utils/color'
import { SCALES } from '../utils/infusion'
import { Leaves } from './Leaves'
import { SearchSelect } from './SearchSelect'

/** Один и тот же чай в двух магазинах рядом: оценка, цена за грамм, настой и вкус по отзывам на покупку там. */
export function ShopCompare({ tea, index }: { tea: TeaDetails; index: WheelIndex }) {
  const [a, setA] = useState(tea.offers[0].shopId)
  const [b, setB] = useState(tea.offers[1].shopId)
  const options = tea.offers.map((o) => ({ value: o.shopId, label: o.shop.title }))
  return (
    <section className="stack" aria-labelledby="compare-h">
      <div className="section-head">
        <h2 id="compare-h">Сравнить магазины</h2>
        <span className="small muted">Тот же чай — по отзывам на покупку в каждом магазине</span>
      </div>
      <div className="compare-grid">
        {[
          [a, setA, b],
          [b, setB, a],
        ].map(([shopId, set, other], i) => (
          <div key={i} className="card stack" style={{ gap: 14 }}>
            <SearchSelect
              aria-label={`Магазин ${i + 1}`}
              options={options.filter((o) => o.value !== other)}
              value={shopId as number}
              onChange={set as (v: number) => void}
            />
            <ShopColumn tea={tea} offer={tea.offers.find((o) => o.shopId === shopId)!} index={index} />
          </div>
        ))}
      </div>
    </section>
  )
}

function ShopColumn({ tea, offer, index }: { tea: TeaDetails; offer: RatedOffer; index: WheelIndex }) {
  const profile = useAsync(() => api.getTeaFlavors(tea.id, offer.shop.name), [tea.id, offer.shop.name])
  const reviews = tea.reviews.filter((r) => r.shopId === offer.shopId)
  const perGram = offer.price != null && offer.weight ? offer.price / offer.weight : null
  const flavors = new Map(profile.data?.flavors.map((s) => [s.slug, s.share]) ?? [])
  const groups = new Map(profile.data?.groups.map((s) => [s.slug, s.share]) ?? [])
  const top = (m: Map<string, number>) => Math.max(0, ...m.values())
  return (
    <>
      <Link to={`/shops/${offer.shop.name}`} className="rank-name">{offer.shop.title}</Link>
      <div className="row">
        <strong style={{ fontSize: 22 }}>{fmtScore(offer.stats.avg)}</strong>
        <Leaves value={offer.stats.avg} />
        <span className="small muted">{reviewsWord(offer.stats.reviews)}</span>
      </div>
      <dl className="compare-facts">
        <dt>Цена</dt>
        <dd>
          {perGram != null ? (
            <>
              <span className="nowrap">{fmtPerGram(perGram)}</span> · <span className="nowrap">{offer.priceLabel}</span>
            </>
          ) : (
            '—'
          )}
        </dd>
        {SCALES.map((s) => {
          const marked = reviews.map((r: Review) => r[s.key]).filter((v): v is number => v != null)
          return [
            <dt key={`${s.key}-t`}>{s.title}</dt>,
            <dd key={`${s.key}-d`}>{marked.length ? `${(marked.reduce((x, y) => x + y, 0) / marked.length).toFixed(1).replace('.', ',')} из 5` : '—'}</dd>,
          ]
        })}
      </dl>
      {profile.data && profile.data.reviews > 0 ? (
        <>
          <FlavorWheel
            index={index}
            label={`Вкус по отзывам на покупку в ${offer.shop.title}`}
            flavorLevel={(sl) => (top(flavors) ? (flavors.get(sl) ?? 0) / top(flavors) : 0)}
            groupLevel={(sl) => (top(groups) ? (groups.get(sl) ?? 0) / top(groups) : 0)}
            marked={(sl) => flavors.has(sl)}
          />
          <div className="row" style={{ gap: 6 }}>
            {profile.data.flavors.slice(0, 6).map((sh) => {
              const e = index.flavor(sh.slug)
              return (
                e && (
                  <span key={sh.slug} className="tag" style={{ background: e.group.color, color: textOn(e.group.color) }}>
                    {e.flavor.title} · {Math.round(sh.share * 100)}%
                  </span>
                )
              )
            })}
          </div>
        </>
      ) : (
        <p className="small muted">{profile.loading ? 'Загружаем…' : 'О вкусе чая из этого магазина пока не писали.'}</p>
      )}
    </>
  )
}
