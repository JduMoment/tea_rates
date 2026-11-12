/**
 * Яндекс Метрика. Работает только на боевом домене — локальная разработка статистику не портит.
 *
 * Сайт — SPA: страница загружается один раз, дальше React Router меняет адрес без перезагрузки.
 * Поэтому init засчитывает первый просмотр, а каждый следующий переход отправляет MetrikaTracker.
 */
import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router'

export const METRIKA_ID = 114161686
const PROD_HOST = '5listov.ru'
/** Заголовок страницы чая появляется после загрузки данных — даём ему время, чтобы в отчётах было имя чая. */
const TITLE_DELAY_MS = 1000

type Ym = ((id: number, method: string, ...args: unknown[]) => void) & { a?: unknown[][]; l?: number }

declare global {
  interface Window {
    ym?: Ym
  }
}

export const metrikaEnabled = () => window.location.hostname === PROD_HOST

/** Подключает счётчик (код из кабинета Метрики, без электронной коммерции — её на сайте нет).
 * Вызывается только после согласия на cookie (CookieBanner). */
export function initMetrika() {
  if (!metrikaEnabled() || window.ym) return
  const ym: Ym = (...args) => {
    ;(ym.a = ym.a || []).push(args)
  }
  ym.l = Date.now()
  window.ym = ym
  const script = document.createElement('script')
  script.async = true
  script.src = `https://mc.yandex.ru/metrika/tag.js?id=${METRIKA_ID}`
  document.head.appendChild(script)
  ym(METRIKA_ID, 'init', {
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    referrer: document.referrer,
    url: window.location.href,
  })
}

/** Отправляет просмотр при каждом переходе внутри сайта. Первый просмотр уже засчитал init. */
export function MetrikaTracker() {
  const location = useLocation()
  const url = location.pathname + location.search + location.hash
  const previous = useRef(url)

  useEffect(() => {
    if (previous.current === url) return
    const from = previous.current
    previous.current = url
    if (!metrikaEnabled() || !window.ym) return
    const referer = window.location.origin + from
    let sent = false
    const send = () => {
      if (sent) return
      sent = true
      window.ym?.(METRIKA_ID, 'hit', window.location.href, { title: document.title, referer })
    }
    const timer = window.setTimeout(send, TITLE_DELAY_MS)
    // Ушли со страницы раньше — просмотр всё равно засчитываем
    return () => {
      window.clearTimeout(timer)
      send()
    }
  }, [url])

  return null
}
