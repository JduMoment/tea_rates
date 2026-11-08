import { useMemo } from 'react'
import * as api from '../api'
import type { Category, FlavorGroupInfo, FlavorInfo, FlavorWheel, TasteInfo, Tea } from '../data/types'
import { fmtPerGram, plural } from '../utils/format'
import { useAsync } from './useAsync'

/** Виды чая (кешируются на всю сессию) + поиск по slug и id. Пока грузятся — пустой список. */
export function useCategories() {
  const res = useAsync(() => api.getCategories(), [])
  return useMemo(() => {
    const list = res.data ?? []
    return {
      list,
      ready: Boolean(res.data),
      bySlug: (slug: string | null | undefined): Category | undefined => list.find((c) => c.slug === slug),
      byId: (id: number): Category | undefined => list.find((c) => c.id === id),
    }
  }, [res.data])
}

export interface FlavorEntry {
  flavor: FlavorInfo
  group: FlavorGroupInfo
  taste: TasteInfo
}

export interface WheelIndex {
  wheel: FlavorWheel
  /** slug дескриптора → он сам, его группа и вкус */
  flavor: (slug: string) => FlavorEntry | undefined
  group: (slug: string) => FlavorGroupInfo | undefined
  taste: (slug: string) => TasteInfo | undefined
  all: FlavorEntry[]
}

export function indexWheel(wheel: FlavorWheel): WheelIndex {
  const tastes = new Map(wheel.tastes.map((t) => [t.slug, t]))
  const all: FlavorEntry[] = wheel.groups.flatMap((group) =>
    group.flavors.map((flavor) => ({ flavor, group, taste: tastes.get(flavor.taste)! })),
  )
  const flavors = new Map(all.map((e) => [e.flavor.slug, e]))
  const groups = new Map(wheel.groups.map((g) => [g.slug, g]))
  return {
    wheel,
    flavor: (slug) => flavors.get(slug),
    group: (slug) => groups.get(slug),
    taste: (slug) => tastes.get(slug),
    all,
  }
}

/** Колесо вкусов с индексом. undefined, пока грузится. */
export function useFlavorWheel(): WheelIndex | undefined {
  const res = useAsync(() => api.getFlavorWheel(), [])
  return useMemo(() => (res.data ? indexWheel(res.data) : undefined), [res.data])
}

/** Подпись «где купить» для карточек: магазин, если он один, иначе их число; и минимальная цена.
 *  count — всегда число магазинов: там, где рядом оценка чая, название магазина читалось бы
 *  как «оценка в этом магазине», хотя она по всем. */
export function offersSummary(tea: Tea) {
  const n = tea.offers.length
  const count = n === 0 ? 'Нет в продаже' : `${n} ${plural(n, 'магазин', 'магазина', 'магазинов')}`
  const shops = n === 1 ? tea.offers[0].shop.title : count
  // Сравниваем за грамм: 1 250 ₽ / 50 г дороже, чем 2 000 ₽ / 100 г. Без цены — не участвуют
  const perGram = (o: Tea['offers'][number]) => (o.price != null && o.weight ? o.price / o.weight : Infinity)
  const priced = tea.offers.filter((o) => perGram(o) < Infinity)
  const cheapest = priced.reduce<Tea['offers'][number] | null>((best, o) => (!best || perGram(o) < perGram(best) ? o : best), null)
  const price = cheapest?.priceLabel ? (priced.length > 1 ? `от ${cheapest.priceLabel}` : cheapest.priceLabel) : ''
  const gram = cheapest ? fmtPerGram(perGram(cheapest)) : ''
  return { shops, count, price, perGram: gram }
}
