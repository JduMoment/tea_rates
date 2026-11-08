export const fmtScore = (v: number) => (v ? v.toFixed(1).replace('.', ',') : '—')

export function plural(n: number, one: string, few: string, many: string) {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return one
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few
  return many
}

export const reviewsWord = (n: number) => `${n} ${plural(n, 'отзыв', 'отзыва', 'отзывов')}`
export const teasWord = (n: number) => `${n} ${plural(n, 'чай', 'чая', 'чаёв')}`

export function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

/** «29 ₽/г», для дешёвых — с копейками: «4,4 ₽/г» */
export function fmtPerGram(perGram: number) {
  const v = perGram >= 10 ? Math.round(perGram).toString() : perGram.toFixed(1).replace('.', ',')
  return `${v} ₽/г`
}
