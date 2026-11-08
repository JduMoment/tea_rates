import { useEffect, useState } from 'react'
import * as api from '../api'
import { SHELF_STATUSES, type ShelfStatus } from '../data/types'

/** «Хочу попробовать / Есть дома / Закончился» на странице чая. Повторный клик убирает из шкафа. */
export function ShelfButtons({ teaId }: { teaId: number }) {
  const [status, setStatus] = useState<ShelfStatus | null | undefined>(undefined)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let alive = true
    api
      .getShelf()
      .then((items) => alive && setStatus(items.find((i) => i.tea.id === teaId)?.status ?? null))
      .catch(() => alive && setStatus(null))
    return () => {
      alive = false
    }
  }, [teaId])

  if (status === undefined) return null

  async function pick(next: ShelfStatus) {
    setBusy(true)
    try {
      if (next === status) {
        await api.removeFromShelf(teaId)
        setStatus(null)
      } else {
        setStatus((await api.putShelf(teaId, next)).status)
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="row" style={{ gap: 6 }} role="group" aria-label="Мои чаи">
      <span className="small muted" style={{ fontWeight: 600 }}>Мои чаи:</span>
      {SHELF_STATUSES.map((s) => (
        <button key={s.id} type="button" className="chip chip-sm" aria-pressed={status === s.id} disabled={busy} onClick={() => pick(s.id)}>
          {s.label}
        </button>
      ))}
    </div>
  )
}
