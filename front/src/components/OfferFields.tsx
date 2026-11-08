import type { ShopBrief } from '../data/types'
import type { OfferDraft } from '../utils/offer'
import { SearchSelect } from './SearchSelect'

/** Магазин, цена на сайте сейчас, ссылка — для нового чая и для «есть ещё в магазине».
 *  Партию здесь не спрашиваем: она у каждой покупки своя и указывается в отзыве. */
export function OfferFields({
  value,
  onChange,
  shops,
}: {
  value: OfferDraft
  onChange: (v: OfferDraft) => void
  /** Из каких магазинов можно выбрать. */
  shops: ShopBrief[]
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
        />
      </label>
      <div className="row">
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
