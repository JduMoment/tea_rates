import { Link } from 'react-router'
import type { ShopBrief } from '../data/types'
import type { OfferDraft } from '../utils/offer'
import { SearchSelect } from './SearchSelect'

/** Магазин, цена на сайте сейчас, ссылка — для нового чая и для «есть ещё в магазине».
 *  Партию здесь не спрашиваем: она у каждой покупки своя и указывается в отзыве. */
export function OfferFields({
  value,
  onChange,
  shops,
  backTo,
}: {
  value: OfferDraft
  onChange: (v: OfferDraft) => void
  /** Из каких магазинов можно выбрать. */
  shops: ShopBrief[]
  /** Куда вернуться после «Добавить магазин» (туда допишется ?shop=<name>). Без него ссылки нет. */
  backTo?: string
}) {
  const set = <K extends keyof OfferDraft>(key: K, v: OfferDraft[K]) => onChange({ ...value, [key]: v })

  return (
    <div className="stack" style={{ gap: 14 }}>
      <label className="field">
        Магазин
        <SearchSelect
          options={shops.map((s) => ({ value: s.id, label: s.title }))}
          value={value.shopId}
          onChange={(id) => set('shopId', id)}
          placeholder="Выберите магазин…"
          notFound="Такого магазина в каталоге нет"
          footer={
            backTo
              ? (q) => (
                  <Link to={`/shops/new?${new URLSearchParams({ back: backTo, ...(q && { title: q }) })}`} style={{ fontWeight: 700 }}>
                    + Нет нужного? Добавить {q ? `«${q}»` : 'магазин'}
                  </Link>
                )
              : undefined
          }
        />
      </label>
      {/* По нижнему краю: подпись цены длиннее и на телефоне переносится — поля всё равно на одной линии */}
      <div className="row" style={{ alignItems: 'flex-end' }}>
        <label className="field" style={{ flex: '1 1 120px' }}>
          Цена на сайте сейчас, ₽ <span className="muted" style={{ fontWeight: 500 }}>необязательно</span>
          <input className="input" type="number" min={1} value={value.price} onChange={(e) => set('price', e.target.value)} />
        </label>
        <label className="field" style={{ flex: '1 1 120px' }}>
          За сколько грамм
          <input className="input" type="number" min={1} required={value.price.trim() !== ''} value={value.weight} onChange={(e) => set('weight', e.target.value)} />
        </label>
      </div>
      <p className="small muted" style={{ margin: 0 }}>Дальше цену обновляют отзывы: в них указывают, сколько заплатили.</p>
      <label className="field">
        Ссылка на чай в магазине <span className="muted" style={{ fontWeight: 500 }}>необязательно</span>
        <input className="input" type="url" placeholder="https://…" value={value.url} onChange={(e) => set('url', e.target.value)} />
      </label>
    </div>
  )
}
