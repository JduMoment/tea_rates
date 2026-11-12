import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import * as api from '../api'
import { useAuth } from '../auth/AuthContext'
import type { RatedOffer, ShopBrief, TeaDetails } from '../data/types'
import { useAsync } from '../hooks/useAsync'
import { usePageTitle } from '../hooks/usePageTitle'
import { useFlavorWheel } from '../hooks/useCatalog'
import { FlavorProfileView } from '../components/FlavorWheel'
import { CupIcon } from '../components/Icons'
import { ImageUpload, ShopLogo } from '../components/CatalogImage'
import { Leaves } from '../components/Leaves'
import { Loading, NotFoundBlock } from '../components/Layout'
import { OfferFields } from '../components/OfferFields'
import { emptyOffer, offerInput, offerPriceText } from '../utils/offer'
import { ReviewForm } from '../components/ReviewForm'
import { ReviewItem } from '../components/ReviewItem'
import { ReviewThanks } from '../components/ReviewThanks'
import { takeDonateAsk } from '../donate'
import { TeaCard } from '../components/TeaCard'
import { BrewingBlock } from '../components/Brewing'
import { InfusionBars } from '../components/Infusion'
import { PriceChart } from '../components/PriceChart'
import { ShelfButtons } from '../components/ShelfButtons'
import { ShopCompare } from '../components/ShopCompare'
import { fmtPerGram, fmtScore, reviewsWord } from '../utils/format'

export function TeaPage() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const wheel = useFlavorWheel()
  const res = useAsync(() => api.getTea(id), [id])
  usePageTitle(res.data?.title)
  const brewing = useAsync(() => api.getBrewing(Number(id)), [id])
  const prices = useAsync(() => api.getPrices(Number(id)), [id])
  const [reviewSort, setReviewSort] = useState<'new' | 'helpful'>('new')
  // «Купили в другом магазине?» — открыть форму, хотя свой отзыв на чай уже есть
  const [anotherShop, setAnotherShop] = useState(false)
  // После нового отзыва: показать «спасибо» (askDonate — с просьбой поддержать проект)
  // teaId — чтобы «спасибо» не переехало на другой чай при переходе по «Другие улуны»
  const [thanks, setThanks] = useState<{ teaId: string; askDonate: boolean } | null>(null)
  // ?edit=<id отзыва> — пришли из профиля по «Изменить»
  const [params, setParams] = useSearchParams()
  const editingId = Number(params.get('edit')) || null
  function editReview(id: number | null) {
    setParams((p) => {
      if (id) p.set('edit', String(id))
      else p.delete('edit')
      return p
    }, { replace: true })
  }
  // Открыли правку — показываем форму (и когда пришли из профиля, как только чай загрузился)
  const loaded = Boolean(res.data)
  useEffect(() => {
    if (editingId && loaded) document.getElementById('review-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [editingId, loaded])

  if (res.loading && !res.data) return <Loading />
  const tea = res.data
  if (!tea) return <NotFoundBlock text="Чай не найден" />

  const mine = user ? tea.reviews.filter((r) => r.userId === user.id) : []
  const editing = mine.find((r) => r.id === editingId) ?? null
  // Свой отзыв уже есть — форму не показываем (свой правят через «Изменить»). Новый отзыв — только
  // о покупке в магазине, где этот чай ещё не оценивали, и по кнопке.
  const reviewed = new Set(mine.map((r) => r.shopId))
  const freeOffers = tea.offers.filter((o) => !reviewed.has(o.shopId))
  const showForm = Boolean(editing) || !user || mine.length === 0 || anotherShop
  const reviews =
    reviewSort === 'helpful' ? [...tea.reviews].sort((a, b) => b.helpful - a.helpful) : tea.reviews
  const pricePoints = prices.data?.reduce((n, s) => n + s.points.length, 0) ?? 0
  // Регалия — лучшее место среди магазинов, где продаётся этот чай
  const best = tea.offers
    .filter((o) => o.shopRank)
    .reduce<RatedOffer | undefined>((a, o) => (!a || o.shopRank! < a.shopRank! ? o : a), undefined)

  return (
    <div className="page">
      <nav className="small muted" aria-label="Навигация">
        <Link to="/teas">Чаи</Link> / <Link to={`/teas?category=${tea.category.slug}`}>{tea.category.plural}</Link> / {tea.title}
      </nav>

      <section className="split">
        <div className="main panel" style={{ background: tea.category.color }}>
          <div className="tea-art">
            <span className="sticker" style={{ fontSize: 22, background: tea.category.color }}>{fmtScore(tea.stats.avg)}</span>
            {tea.imageUrl ? <img src={tea.imageUrl} alt={tea.title} className="tea-photo" /> : <CupIcon size={150} color={tea.category.ink} />}
          </div>
          <div className="stack" style={{ flex: '1 1 300px' }}>
            <div className="row" style={{ gap: 8 }}>
              <span className="tag" style={{ background: 'var(--surface)', color: tea.category.ink }}>{tea.category.name}</span>
              {best && (
                <Link
                  to={`/rankings/categories/${tea.category.slug}`}
                  className="tag regalia"
                  style={{ background: tea.category.ink }}
                  title="Сравнить магазины"
                >
                  ★ {best.shop.title} — {best.shopRank}-е место среди магазинов «{tea.category.name}»
                </Link>
              )}
            </div>
            <h1 style={{ fontSize: 'clamp(36px, 4.6vw, 56px)' }}>{tea.title}</h1>
            <div className="row">
              <Leaves value={tea.stats.avg} size={22} />
              <strong style={{ fontSize: 20 }}>{fmtScore(tea.stats.avg)}</strong>
              <span className="muted">· {reviewsWord(tea.stats.reviews)} из всех магазинов</span>
            </div>
            {tea.description && <p>{tea.description}</p>}
            {tea.region && (
              <dl style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 16px', margin: 0 }}>
                <dt className="muted">Регион</dt><dd style={{ margin: 0 }}>{tea.region}</dd>
              </dl>
            )}
            <div className="row">
              <a href="#offers" className="btn">Где купить · {tea.offers.length}</a>
              {user && <Link to={`/diary?add=${tea.id}`} className="btn btn-ghost">В дневник</Link>}
            </div>
            {user && <ShelfButtons teaId={tea.id} />}
            {user && !tea.imageUrl && (
              <ImageUpload label="Загрузить фото чая" upload={(f) => api.uploadTeaImage(tea.id, f)} onDone={res.reload} />
            )}
          </div>
          {/* Вкусовой профиль — главное о чае, поэтому прямо в шапке, отдельной строкой */}
          <section style={{ flexBasis: '100%', minWidth: 0 }} aria-label="Вкусовой профиль">
            {wheel ? <FlavorProfileView index={wheel} profile={tea.flavorProfile} /> : <Loading />}
          </section>
          {tea.infusion.reviews > 0 && (
            <section className="card" style={{ flexBasis: '100%', minWidth: 0 }} aria-label="Настой">
              <InfusionBars stats={tea.infusion} />
            </section>
          )}
        </div>
      </section>

      {brewing.data && <BrewingBlock teaId={tea.id} brewing={brewing.data} />}

      <Offers tea={tea} onChanged={res.reload} />

      {prices.data && pricePoints >= 2 && (
        <section className="card stack" aria-labelledby="prices-h">
          <div className="section-head" style={{ margin: 0 }}>
            <h2 id="prices-h">История цены</h2>
            <span className="small muted">За грамм — по ценам из отзывов и на сайте магазина</span>
          </div>
          <PriceChart data={prices.data} />
        </section>
      )}

      {wheel && tea.offers.length >= 2 && <ShopCompare tea={tea} index={wheel} />}

      <section className="stack" aria-labelledby="reviews-h">
        <div className="section-head">
          <h2 id="reviews-h">Отзывы</h2>
          {tea.reviews.length > 1 && (
            <div className="row" style={{ gap: 6 }} role="group" aria-label="Порядок отзывов">
              <button type="button" className="chip chip-sm" aria-pressed={reviewSort === 'new'} onClick={() => setReviewSort('new')}>Сначала новые</button>
              <button type="button" className="chip chip-sm" aria-pressed={reviewSort === 'helpful'} onClick={() => setReviewSort('helpful')}>Сначала полезные</button>
            </div>
          )}
        </div>
        <div className="stack">
            {tea.reviews.length === 0 && <div className="empty">Отзывов пока нет — будьте первым.</div>}
            {reviews.map((r) => (
              <ReviewItem
                key={r.id}
                review={r}
                onEdit={user && r.userId === user.id ? () => editReview(r.id) : undefined}
                onDelete={
                  user && r.userId === user.id
                    ? async () => {
                        await api.deleteReview(r.id)
                        res.reload()
                      }
                    : undefined
                }
              />
            ))}
        </div>
        {thanks?.teaId === id && <ReviewThanks askDonate={thanks.askDonate} onClose={() => setThanks(null)} />}
        {showForm && (editing || freeOffers.length > 0) ? (
          <ReviewForm
            key={`${tea.id}-${editing?.id ?? 'new'}`}
            teaId={tea.id}
            offers={freeOffers}
            editing={editing}
            onSaved={(created) => {
              setAnotherShop(false)
              if (created) setThanks({ teaId: id, askDonate: takeDonateAsk() })
              res.reload()
            }}
            onCancelEdit={() => editReview(null)}
          />
        ) : (
          mine.length > 0 &&
          freeOffers.length > 0 && (
            <div>
              <button type="button" className="btn btn-ghost" onClick={() => setAnotherShop(true)}>
                Купили в другом магазине? Написать отзыв
              </button>
            </div>
          )
        )}
      </section>

      {tea.alternatives.length > 0 && (
        <section>
          <div className="section-head">
            <h2>Другие {tea.category.plural.toLowerCase()}</h2>
            <Link to={`/teas?category=${tea.category.slug}`}>Все {tea.category.plural.toLowerCase()} →</Link>
          </div>
          <div className="grid">
            {tea.alternatives.map((t) => <TeaCard key={t.id} tea={t} />)}
          </div>
        </section>
      )}
    </div>
  )
}

/** «Где купить»: магазины с ценой и оценкой этого чая именно у них + добавить ещё один. */
function Offers({ tea, onChanged }: { tea: TeaDetails; onChanged: () => void }) {
  const { user } = useAuth()
  // ?shop=<name> — вернулись после «Добавить магазин»: сразу открываем форму с ним
  const [params] = useSearchParams()
  const [adding, setAdding] = useState(Boolean(params.get('shop')))

  return (
    <section className="stack" id="offers" aria-labelledby="offers-h">
      <div className="section-head">
        <h2 id="offers-h">Где купить</h2>
        <span className="small muted">Оценка — по отзывам на покупку именно в этом магазине</span>
      </div>
      <ol className="stack rank-list">
        {tea.offers.map((o, i) => (
          <li key={o.id} className="rank-row" style={i === 0 && o.stats.reviews ? { background: tea.category.color } : undefined}>
            <div style={{ flex: '2 1 220px', minWidth: 0 }} className="stack">
              <span className="row" style={{ gap: 10, flexWrap: 'nowrap' }}>
                <ShopLogo shop={o.shop} size={32} />
                <Link to={`/shops/${o.shop.name}`} className="rank-name">{o.shop.title}</Link>
              </span>
              <span className="small muted">
                {[
                  offerPriceText(o),
                  o.price != null && o.weight ? fmtPerGram(o.price / o.weight) : '',
                  o.shopRank ? `${o.shopRank}-е место по виду «${tea.category.name}»` : '',
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
            </div>
            <div style={{ flex: '1 1 180px' }} className="row">
              <strong style={{ fontSize: 20 }}>{fmtScore(o.stats.avg)}</strong>
              <Leaves value={o.stats.avg} />
              <span className="small muted">{reviewsWord(o.stats.reviews)}</span>
            </div>
            <div className="row" style={{ flex: '0 1 auto' }}>
              {o.url && <a href={o.url} target="_blank" rel="noreferrer" style={{ fontWeight: 700 }}>Купить ↗</a>}
            </div>
          </li>
        ))}
      </ol>
      {user &&
        (adding ? (
          <AddOfferForm
            tea={tea}
            onCancel={() => setAdding(false)}
            onSaved={() => {
              setAdding(false)
              onChanged()
            }}
          />
        ) : (
          <div id="add-offer">
            <button type="button" className="btn btn-ghost" onClick={() => setAdding(true)}>+ Этот чай есть в другом магазине</button>
          </div>
        ))}
    </section>
  )
}

function AddOfferForm({ tea, onSaved, onCancel }: { tea: TeaDetails; onSaved: () => void; onCancel: () => void }) {
  const shops = useAsync(() => api.getShops(), [])
  const [params] = useSearchParams()
  const [offer, setDraft] = useState(emptyOffer())
  const preset = shops.data?.find((s) => s.name === params.get('shop'))
  const draft = offer.shopId === 0 && preset ? { ...offer, shopId: preset.id } : offer
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const taken = new Set(tea.offers.map((o) => o.shopId))
  const free: ShopBrief[] = (shops.data ?? []).filter((s) => !taken.has(s.id)).sort((a, b) => a.title.localeCompare(b.title, 'ru'))

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!draft.shopId) return setError('Выберите магазин')
    setBusy(true)
    setError(null)
    try {
      await api.addOffer(tea.id, offerInput(draft))
      onSaved()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form id="add-offer" className="card stack" onSubmit={submit} style={{ maxWidth: 560 }}>
      <h3>Где ещё продаётся «{tea.title}»</h3>
      {shops.data && free.length === 0 ? (
        <p className="muted">
          Этот чай уже есть во всех магазинах каталога.{' '}
          <Link to={`/shops/new?${new URLSearchParams({ back: `/teas/${tea.id}` })}`}>Добавить новый магазин</Link>
        </p>
      ) : (
        <OfferFields value={draft} onChange={setDraft} shops={free} backTo={`/teas/${tea.id}`} />
      )}
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row">
        <button className="btn" disabled={busy || free.length === 0}>{busy ? 'Сохраняем…' : 'Добавить'}</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Отмена</button>
      </div>
    </form>
  )
}
