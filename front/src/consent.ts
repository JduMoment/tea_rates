/**
 * Согласие на cookie аналитики (Яндекс Метрика).
 *
 * Сессионная cookie входа — необходимая, на неё согласие не спрашиваем.
 * Метрика ставит свои cookie, поэтому подключаем её только после «Принять».
 */
import { useSyncExternalStore } from 'react'

export type Consent = 'all' | 'necessary'

const KEY = 'cookie-consent'
const listeners = new Set<() => void>()
/** Запасное хранилище, если localStorage недоступен (приватный режим): выбор живёт до перезагрузки. */
let memory: Consent | null = null

export function getConsent(): Consent | null {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'all' || v === 'necessary' ? v : null
  } catch {
    return memory
  }
}

export function setConsent(value: Consent | null) {
  memory = value
  try {
    if (value) localStorage.setItem(KEY, value)
    else localStorage.removeItem(KEY)
  } catch {
    // остаётся memory
  }
  listeners.forEach((l) => l())
}

/** Отказ после согласия: стираем cookie Метрики (_ym_uid, _ym_d…). Сам скрипт выгрузит только перезагрузка. */
export function clearAnalyticsCookies() {
  const host = window.location.hostname
  for (const part of document.cookie.split(';')) {
    const name = part.split('=')[0].trim()
    if (!name.startsWith('_ym')) continue
    for (const domain of ['', `; domain=${host}`, `; domain=.${host}`]) {
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/${domain}`
    }
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Текущий выбор; null — ещё не выбирали, показываем плашку. */
export function useConsent(): Consent | null {
  return useSyncExternalStore(subscribe, getConsent)
}
