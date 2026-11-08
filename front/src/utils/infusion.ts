import type { Review } from '../data/types'

/** Шкалы настоя 1–5: от чего к чему. */
export const SCALES = [
  { key: 'body', title: 'Тело', low: 'лёгкое', high: 'плотное' },
  { key: 'strength', title: 'Насыщенность', low: 'пустой', high: 'крепкий' },
  { key: 'aftertaste', title: 'Послевкусие', low: 'короткое', high: 'долгое' },
] as const

export type ScaleKey = (typeof SCALES)[number]['key']
export type InfusionValue = Record<ScaleKey, number | null>

export const emptyInfusion = (): InfusionValue => ({ body: null, strength: null, aftertaste: null })

/** Строка в отзыве: «тело 4/5 · насыщенность 3/5». */
export function infusionText(r: Pick<Review, ScaleKey>) {
  return SCALES.filter((s) => r[s.key] != null)
    .map((s) => `${s.title.toLowerCase()} ${r[s.key]}/5`)
    .join(' · ')
}
