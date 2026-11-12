/** Донаты через CloudTips (Т-Банк). */
export const DONATE_URL = 'https://pay.cloudtips.ru/p/fbab7e79'

const KEY = 'donate-asked-at'
/** Просим о поддержке не чаще раза в месяц — активные авторы пишут отзывы часто, надоедать не хочется. */
const ASK_EVERY_MS = 30 * 24 * 60 * 60 * 1000

/** Пора ли снова показать просьбу; если да — запоминаем, что показали. */
export function takeDonateAsk(now = Date.now()): boolean {
  try {
    const last = Number(localStorage.getItem(KEY) ?? 0)
    if (now - last < ASK_EVERY_MS) return false
    localStorage.setItem(KEY, String(now))
    return true
  } catch {
    return true
  }
}
