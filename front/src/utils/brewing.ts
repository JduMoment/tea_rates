import type { Brewing } from '../data/types'

/** Параметры, которые подставим в запись дневника: сначала как у тех, кому понравилось, потом как у всех,
 *  иначе — середина типичного для вида чая (на гайвань 100 мл). */
export function suggestedParams(b: Brewing) {
  const src = b.liked ?? b.community
  if (src) {
    const volume = src.volume ?? 100
    const grams = src.gramsPer100 != null ? Math.round(((src.gramsPer100 * volume) / 100) * 2) / 2 : src.grams
    return { water: src.water, grams, volume, infusions: src.infusions }
  }
  const mid = ([a, b2]: [number, number]) => (a + b2) / 2
  return {
    water: Math.round(mid(b.typical.water)),
    grams: Math.round(mid(b.typical.gramsPer100) * 2) / 2,
    volume: 100,
    infusions: Math.round(mid(b.typical.infusions)),
  }
}
