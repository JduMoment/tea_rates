import { useEffect } from 'react'

const SITE = '5 листов'

/** Заголовок вкладки: «Габа Алишань — 5 листов». Без аргумента — общий заголовок сайта. */
export function usePageTitle(title?: string | null) {
  useEffect(() => {
    document.title = title ? `${title} — ${SITE}` : `${SITE} — рейтинг чаёв по магазинам`
  }, [title])
}
