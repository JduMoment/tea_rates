/** Черновик формы «чай в магазине» и его превращение в тело запроса; подпись цены предложения. */
import type { OfferInput } from '../api'
import type { Offer } from '../data/types'

export interface OfferDraft {
  shopId: number
  price: string
  weight: string
  url: string
}

export const emptyOffer = (shopId = 0): OfferDraft => ({
  shopId,
  price: '',
  weight: '50',
  url: '',
})

/** Черновик формы → тело запроса. Цена необязательна; без цены вес не отправляем. */
export function offerInput(d: OfferDraft): OfferInput & { shopId: number } {
  const priced = d.price.trim() !== ''
  return {
    shopId: d.shopId,
    price: priced ? Number(d.price) : null,
    weight: priced ? Number(d.weight) : null,
    url: d.url.trim() || null,
  }
}

/** «1 250 ₽ / 50 г · по отзыву, октябрь 2025» — цена с датой и источником, или '' если цены нет. */
export function offerPriceText(o: Offer): string {
  if (!o.priceLabel) return ''
  const when = o.priceDate ? fmtMonth(o.priceDate) : ''
  const source = o.priceSource === 'review' ? 'по отзыву' : 'при добавлении'
  return when ? `${o.priceLabel} · ${source}, ${when}` : o.priceLabel
}

/** «октябрь 2025» */
function fmtMonth(iso: string) {
  return new Date(iso).toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' }).replace(/\s*г\.$/, '')
}
