import { useEffect, useMemo, useState } from 'react'
import type { ShopBrief } from '../data/types'
import { StoreIcon } from './Icons'

const MAX_MB = 10
const TYPES = 'image/jpeg,image/png,image/webp'

/** Проверка до отправки — те же правила, что на сервере. null — файл подходит. */
function imageProblem(file: File): string | null {
  if (!TYPES.split(',').includes(file.type)) return 'Подойдут JPEG, PNG или WebP'
  if (file.size > MAX_MB * 1024 * 1024) return `Файл больше ${MAX_MB} МБ`
  return null
}

/** Поле формы «картинка»: выбрать файл, увидеть превью. Сама загрузка — сразу после создания чая/магазина. */
export function ImageField({ label, hint, file, onChange }: { label: string; hint: string; file: File | null; onChange: (f: File | null) => void }) {
  const [error, setError] = useState<string | null>(null)
  const preview = useObjectUrl(file)
  return (
    <div className="field">
      {label} <span className="muted" style={{ fontWeight: 500 }}>необязательно</span>
      <div className="row" style={{ gap: 14 }}>
        {preview && <img src={preview} alt="" className="image-preview" />}
        <label className="btn btn-ghost btn-sm">
          {file ? 'Выбрать другую' : 'Выбрать файл'}
          <input
            type="file"
            accept={TYPES}
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null
              e.target.value = ''
              const problem = f && imageProblem(f)
              setError(problem || null)
              if (!problem) onChange(f)
            }}
          />
        </label>
        {file && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => onChange(null)}>Без картинки</button>
        )}
      </div>
      <span className="small muted" style={{ fontWeight: 500 }}>{hint}</span>
      {error && <span className="error" role="alert">{error}</span>}
    </div>
  )
}

/** Кнопка «Загрузить» на странице чая или магазина, пока картинки нет: выбрал файл — сразу отправили.
 *  Загруженную заменить нельзя, поэтому кнопку показывают только при пустой картинке. */
export function ImageUpload({ label, upload, onDone }: { label: string; upload: (f: File) => Promise<unknown>; onDone: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  return (
    <span className="stack" style={{ gap: 4 }}>
      <label className="btn btn-ghost btn-sm" aria-disabled={busy} style={{ alignSelf: 'flex-start' }}>
        {busy ? 'Загружаем…' : label}
        <input
          type="file"
          accept={TYPES}
          hidden
          disabled={busy}
          onChange={async (e) => {
            const f = e.target.files?.[0]
            e.target.value = ''
            if (!f) return
            const problem = imageProblem(f)
            if (problem) return setError(problem)
            setBusy(true)
            setError(null)
            try {
              await upload(f)
              onDone()
            } catch (err) {
              setError((err as Error).message)
            } finally {
              setBusy(false)
            }
          }}
        />
      </label>
      {error && <span className="error small" role="alert">{error}</span>}
    </span>
  )
}

/** Логотип магазина или, если его нет, значок магазина в кружке. */
export function ShopLogo({ shop, size = 44 }: { shop: ShopBrief; size?: number }) {
  if (shop.logoUrl) {
    return <img src={shop.logoUrl} alt="" className="shop-logo" style={{ width: size, height: size }} loading="lazy" />
  }
  return (
    <span className="cat-dot" style={{ background: 'var(--accent)', width: size, height: size, flex: 'none' }} aria-hidden="true">
      <StoreIcon size={Math.round(size * 0.45)} />
    </span>
  )
}

function useObjectUrl(file: File | null) {
  const url = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url)
    },
    [url],
  )
  return url
}
