/** Авторизация — настоящий бэкенд (FastAPI, сессия в HttpOnly-cookie). */
import type { User } from '../data/types'
import { ApiError } from './errors'
import { http } from './http'

/** GET /api/auth/me — null, если не вошли */
export async function getCurrentUser(): Promise<User | null> {
  try {
    return await http<User>('/auth/me')
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null
    throw e
  }
}

/** POST /api/auth/login */
export const login = (email: string, password: string) =>
  http<User>('/auth/login', { method: 'POST', body: { email, password } })

/** POST /api/auth/register */
export const register = (name: string, email: string, password: string) =>
  http<User>('/auth/register', { method: 'POST', body: { name, email, password } })

/** POST /api/auth/logout */
export const logout = () => http<void>('/auth/logout', { method: 'POST' })

/** Вход через Яндекс ID: обычный переход по ссылке, дальше редиректы делает бэкенд. */
export const yandexLoginUrl = (next: string) => `/api/auth/oauth/yandex/start?${new URLSearchParams({ next })}`

/** Коды из /login?oauth_error=… (их ставит бэкенд, если вход через Яндекс не удался) */
export const OAUTH_ERRORS: Record<string, string> = {
  denied: 'Вход через Яндекс отменён',
  state: 'Вход через Яндекс занял слишком долго — попробуйте ещё раз',
  no_email: 'Яндекс не передал почту, без неё войти не получится',
  unavailable: 'Вход через Яндекс сейчас недоступен',
  provider: 'Не удалось войти через Яндекс — попробуйте ещё раз',
}

/** POST /api/auth/password/forgot — письмо со ссылкой (ответ одинаковый, есть такая почта или нет) */
export const forgotPassword = (email: string) =>
  http<void>('/auth/password/forgot', { method: 'POST', body: { email } })

/** POST /api/auth/password/reset — новый пароль по ссылке; сразу входим */
export const resetPassword = (token: string, password: string) =>
  http<User>('/auth/password/reset', { method: 'POST', body: { token, password } })
