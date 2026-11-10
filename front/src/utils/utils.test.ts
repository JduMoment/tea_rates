import { describe, expect, it } from 'vitest'
import type { Brewing } from '../data/types'
import { suggestedParams } from './brewing'
import { textOn } from './color'
import { experienceLine, fmtPerGram, plural } from './format'
import { infusionText } from './infusion'

const typical: Brewing['typical'] = { water: [90, 95], gramsPer100: [6, 7], infusions: [7, 8] }

describe('suggestedParams', () => {
  it('без записей — середина типичного на гайвань 100 мл', () => {
    expect(suggestedParams({ category: 'Улуны', typical, community: null, liked: null })).toEqual({
      water: 93,
      grams: 6.5,
      volume: 100,
      infusions: 8,
    })
  })

  it('предпочитает тех, кому понравилось, и пересчитывает граммы на их объём', () => {
    const community = { entries: 5, people: 3, water: 90, grams: 5, infusions: 6, volume: 100, gramsPer100: 5 }
    const liked = { ...community, water: 95, volume: 150, gramsPer100: 6 }
    expect(suggestedParams({ category: 'Улуны', typical, community, liked })).toEqual({
      water: 95,
      grams: 9,
      volume: 150,
      infusions: 6,
    })
  })

  it('объём никто не указал — граммы как есть, посуда 100 мл', () => {
    const community = { entries: 3, people: 2, water: 90, grams: 4.5, infusions: 5, volume: null, gramsPer100: null }
    expect(suggestedParams({ category: 'Красные', typical, community, liked: null }).grams).toBe(4.5)
  })
})

describe('форматирование', () => {
  it('цена за грамм', () => {
    expect(fmtPerGram(29.4)).toBe('29 ₽/г')
    expect(fmtPerGram(4.4)).toBe('4,4 ₽/г')
  })

  it('склонения', () => {
    expect([1, 2, 5, 11, 21, 22, 112].map((n) => plural(n, 'отзыв', 'отзыва', 'отзывов'))).toEqual([
      'отзыв', 'отзыва', 'отзывов', 'отзывов', 'отзыв', 'отзыва', 'отзывов',
    ])
  })

  it('шкалы настоя в отзыве — только отмеченные', () => {
    expect(infusionText({ body: 4, strength: null, aftertaste: 5, astringency: null })).toBe('тело 4/5 · послевкусие 5/5')
    expect(infusionText({ body: null, strength: null, aftertaste: null, astringency: null })).toBe('')
  })

  it('текст на цветной плашке читается', () => {
    expect(textOn('#fbf8f0')).toBe('#22301a')
    expect(textOn('#22301a')).toBe('#ffffff')
  })
})

describe('experienceLine', () => {
  it('опытный автор: всё и приписка про вид', () => {
    expect(experienceLine({ teas: 23, kinds: 6, shops: 4, sameKind: 8, kindGenitive: 'шу пуэров' })).toBe(
      '23 чая · 6 видов · 4 магазина · из\u00a0них шу\u00a0пуэров\u00a0—\u00a08',
    )
  })

  it('новичок: без единиц и без приписки', () => {
    expect(experienceLine({ teas: 1, kinds: 1, shops: 1, sameKind: 1, kindGenitive: 'габ' })).toBe('1 чай')
  })
})
