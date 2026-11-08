import { useEffect, useState } from 'react'

/**
 * Простой загрузчик данных: перезапускается при смене deps.
 * Пока идёт новый запрос, отдаёт предыдущие данные (loading = true).
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [tick, setTick] = useState(0)
  const key = JSON.stringify([...deps, tick])
  const [state, setState] = useState<{ key: string | null; data: T | undefined; error: string | null }>({
    key: null,
    data: undefined,
    error: null,
  })

  useEffect(() => {
    let alive = true
    fn()
      .then((data) => alive && setState({ key, data, error: null }))
      .catch((e: unknown) => alive && setState({ key, data: undefined, error: String((e as Error)?.message ?? e) }))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return {
    data: state.data,
    error: state.error,
    loading: state.key !== key,
    reload: () => setTick((t) => t + 1),
  }
}
