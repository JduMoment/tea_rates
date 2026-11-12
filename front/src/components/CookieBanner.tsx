import { useEffect } from 'react'
import { Link } from 'react-router'
import { clearAnalyticsCookies, setConsent, useConsent, type Consent } from '../consent'
import { initMetrika } from '../metrika'

/** Сохраняет выбор. Отказ после согласия: Метрика уже загружена — стираем её cookie и перезагружаем страницу. */
export function choose(value: Consent) {
  const wasLoaded = Boolean(window.ym)
  setConsent(value)
  if (value === 'necessary') {
    clearAnalyticsCookies()
    if (wasLoaded) window.location.reload()
  }
}

/** Плашка внизу экрана, пока посетитель не выбрал. После «Принять» включает Метрику. */
export function CookieBanner() {
  const consent = useConsent()

  useEffect(() => {
    if (consent === 'all') initMetrika()
  }, [consent])

  if (consent) return null
  return (
    <div className="cookie-banner" role="region" aria-label="Согласие на cookie">
      <p>
        Мы используем cookie: без них не работает вход на сайт, а с вашего согласия — ещё и Яндекс Метрика, чтобы
        понимать, какие страницы полезны. <Link to="/privacy">Подробнее</Link>
      </p>
      <div className="cookie-banner-actions">
        <button type="button" className="btn btn-sm" onClick={() => choose('all')}>
          Принять
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => choose('necessary')}>
          Только необходимые
        </button>
      </div>
    </div>
  )
}
