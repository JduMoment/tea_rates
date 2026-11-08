import { ApiError } from './errors'

interface ValidationIssue {
  loc?: (string | number)[]
  msg?: string
}

/** Достаёт человекочитаемый текст из ответа FastAPI ({detail: string | ValidationIssue[]}). */
function messageFrom(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return (detail as ValidationIssue[])
      .map((d) => (d.msg ?? '').replace(/^Value error, /, ''))
      .filter(Boolean)
      .join('. ')
  }
  if (status >= 500) return 'Сервер недоступен, попробуйте позже'
  return `Ошибка ${status}`
}

export async function http<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, {
      method: init.method ?? 'GET',
      credentials: 'same-origin',
      headers: init.body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    })
  } catch {
    throw new ApiError('Нет связи с сервером', 0)
  }
  if (res.status === 204) return undefined as T
  const body: unknown = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(messageFrom(body, res.status), res.status)
  return body as T
}
