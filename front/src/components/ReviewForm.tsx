import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router'
import * as api from '../api'
import { useAuth } from '../auth/AuthContext'
import { SEASONS, type Offer, type Review, type Season } from '../data/types'
import { useFlavorWheel } from '../hooks/useCatalog'
import { FlavorPicker } from './FlavorWheel'
import { InfusionInput } from './Infusion'
import { emptyInfusion } from '../utils/infusion'
import { LeafInput } from './Leaves'
import { SearchSelect } from './SearchSelect'

export function ReviewForm({
  teaId,
  offers,
  editing,
  onSaved,
  onCancelEdit,
}: {
  teaId: number
  /** Магазины, где продаётся чай и где я его ещё не оценивал, — отзыв на покупку в одном из них. */
  offers: Offer[]
  /** Правим этот отзыв: форма заполнена им, магазин не меняется, дата остаётся. Форму пересоздают по key. */
  editing?: Review | null
  onSaved: () => void
  onCancelEdit?: () => void
}) {
  const { user } = useAuth()
  const location = useLocation()
  const wheel = useFlavorWheel()
  const str = (n: number | null | undefined) => (n == null ? '' : String(n))
  const [shopId, setShopId] = useState(editing?.shopId ?? (offers.length === 1 ? offers[0].shopId : 0))
  const [rating, setRating] = useState(editing?.rating ?? 0)
  const [text, setText] = useState(editing?.text ?? '')
  const [flavors, setFlavors] = useState<string[]>(editing?.flavors ?? [])
  const [tastes, setTastes] = useState<string[]>(editing?.tastes ?? [])
  // Покупка — необязательно: цена (вместе с весом) и партия
  const [price, setPrice] = useState(str(editing?.price))
  const [weight, setWeight] = useState(str(editing?.weight))
  const [harvestYear, setHarvestYear] = useState(str(editing?.harvestYear))
  const [harvestSeason, setHarvestSeason] = useState<Season | ''>(editing?.harvestSeason ?? '')
  const [infusion, setInfusion] = useState(
    editing
      ? { body: editing.body, strength: editing.strength, aftertaste: editing.aftertaste, astringency: editing.astringency }
      : emptyInfusion(),
  )
  // Новые фото — загружаются после сохранения отзыва (нужен его id)
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!user) {
    return (
      <div className="card stack" style={{ background: 'var(--accent-soft)' }}>
        <h3>Пробовали этот чай?</h3>
        <p className="muted">Войдите, чтобы оставить отзыв, отметить ноты вкуса и добавить чай в дневник.</p>
        <div className="row">
          <Link to="/login" state={{ from: location.pathname }} className="btn">Войти</Link>
          <Link to="/register" state={{ from: location.pathname }} className="btn btn-ghost">Регистрация</Link>
        </div>
      </div>
    )
  }

  const replacing = editing
  const year = new Date().getFullYear()
  const kept = replacing?.photos ?? []
  const room = MAX_PHOTOS - kept.length

  function addFiles(list: FileList | null) {
    if (!list) return
    const picked = [...files, ...Array.from(list)]
    if (picked.length > room) setError(`К отзыву — не больше ${MAX_PHOTOS} фото`)
    setFiles(picked.slice(0, room))
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!shopId) return setError('Выберите магазин, где купили чай')
    const priced = price.trim() !== ''
    if (priced !== (weight.trim() !== '')) return setError('Укажите и цену, и сколько грамм — или оставьте оба поля пустыми')
    setBusy(true)
    setError(null)
    try {
      const data = {
        rating,
        text,
        flavors,
        tastes,
        price: priced ? Number(price) : null,
        weight: priced ? Number(weight) : null,
        harvestYear: harvestYear ? Number(harvestYear) : null,
        harvestSeason: harvestSeason || null,
        ...infusion,
      }
      const review = editing ? await api.editReview(editing.id, data) : await api.addReview(teaId, { shopId, ...data })
      // Фото — по одному: если одно не подошло, остальные всё равно загрузятся
      const failed: string[] = []
      for (const f of files) {
        try {
          await api.uploadReviewPhoto(review.id, f)
        } catch (err) {
          failed.push(`${f.name}: ${(err as Error).message}`)
        }
      }
      setRating(0)
      setText('')
      setFlavors([])
      setTastes([])
      setPrice('')
      setWeight('')
      setHarvestYear('')
      setHarvestSeason('')
      setInfusion(emptyInfusion())
      setFiles([])
      if (failed.length) setError(`Отзыв сохранён, но не все фото загрузились. ${failed.join('; ')}`)
      onSaved()
      if (editing && !failed.length) onCancelEdit?.()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card review-form" id="review-form" onSubmit={submit}>
      {/* Слева — поля и кнопка (липкие, чтобы кнопка была под рукой), справа — колесо нот */}
      <div className="stack review-form-main">
        <h3>{editing ? 'Правка отзыва' : 'Ваш отзыв'}</h3>
        {editing ? (
          <p className="small">
            <span className="muted">Куплен в </span>
            <strong>{editing.shop.title}</strong>
            <span className="muted"> · дата отзыва не изменится, рядом появится пометка «изменён»</span>
          </p>
        ) : (
          <>
            <label className="field">
              Где купили
              <SearchSelect
                options={offers.map((o) => ({ value: o.shopId, label: o.shop.title }))}
                value={shopId}
                onChange={setShopId}
                placeholder="Выберите магазин…"
              />
            </label>
            <p className="small muted" style={{ marginTop: -6 }}>
              Нет нужного магазина? <a href="#add-offer">Добавьте его</a> в блоке «Где купить».
            </p>
          </>
        )}
        <LeafInput value={rating} onChange={setRating} />
        <label className="field">
          Впечатления
          <textarea className="textarea" rows={6} value={text} onChange={(e) => setText(e.target.value)} placeholder="Как раскрывался, сколько проливов держит, стоит ли своих денег…" />
        </label>
        <fieldset className="stack purchase" style={{ gap: 8 }}>
          <legend className="field" style={{ display: 'block' }}>
            Вкус <span className="muted" style={{ fontWeight: 500 }}>· что чувствуется на языке, можно несколько</span>
          </legend>
          <div className="row" style={{ gap: 8 }} role="group" aria-label="Вкус">
            {wheel?.wheel.tastes.map((t) => (
              <button
                key={t.slug}
                type="button"
                className="chip"
                aria-pressed={tastes.includes(t.slug)}
                onClick={() => setTastes((cur) => (cur.includes(t.slug) ? cur.filter((x) => x !== t.slug) : [...cur, t.slug]))}
              >
                <span className="dot" style={{ background: t.color }} aria-hidden="true" />
                {t.title}
              </button>
            ))}
          </div>
          <span className="small muted">Умами — «бульонность», насыщенный вкус, как у водорослей или хорошего зелёного чая.</span>
        </fieldset>
        <fieldset className="stack purchase" style={{ gap: 10 }}>
          <legend className="field" style={{ display: 'block' }}>
            Покупка <span className="muted" style={{ fontWeight: 500 }}>· необязательно</span>
          </legend>
          <div className="row" style={{ gap: 10 }}>
            <label className="field" style={{ flex: '1 1 120px' }}>
              Заплатили, ₽
              <input className="input" type="number" min={1} value={price} onChange={(e) => setPrice(e.target.value)} />
            </label>
            <label className="field" style={{ flex: '1 1 100px' }}>
              За грамм
              <input className="input" type="number" min={1} placeholder="50" value={weight} onChange={(e) => setWeight(e.target.value)} />
            </label>
          </div>
          <div className="row" style={{ gap: 10 }}>
            <label className="field" style={{ flex: '1 1 100px' }}>
              Год сбора
              <input className="input" type="number" min={1900} max={year} placeholder={String(year)} value={harvestYear} onChange={(e) => setHarvestYear(e.target.value)} />
            </label>
            <label className="field" style={{ flex: '1 1 120px' }}>
              Сезон
              <select className="select" value={harvestSeason} onChange={(e) => setHarvestSeason(e.target.value as Season | '')}>
                <option value="">Не знаю</option>
                {SEASONS.map((s) => (
                  <option key={s.id} value={s.id}>{s.label}</option>
                ))}
              </select>
            </label>
          </div>
        </fieldset>
        <InfusionInput value={infusion} onChange={setInfusion} />
        <div className="stack" style={{ gap: 8 }}>
          <span className="field" style={{ display: 'block' }}>
            Фото <span className="muted" style={{ fontWeight: 500 }}>· до {MAX_PHOTOS}, необязательно</span>
          </span>
          <div className="review-photos">
            {kept.map((p) => (
              <span key={p.id} className="review-photo">
                <img src={p.thumbUrl} alt="" />
                <button
                  type="button"
                  className="photo-remove"
                  aria-label="Удалить фото"
                  onClick={async () => {
                    await api.deleteReviewPhoto(replacing!.id, p.id)
                    onSaved()
                  }}
                >
                  ✕
                </button>
              </span>
            ))}
            {files.map((f, i) => (
              <span key={`${f.name}-${i}`} className="review-photo">
                <FilePreview file={f} />
                <button type="button" className="photo-remove" aria-label="Убрать фото" onClick={() => setFiles(files.filter((_, j) => j !== i))}>
                  ✕
                </button>
              </span>
            ))}
            {files.length < room && (
              <label className="review-photo photo-add">
                + фото
                <input type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={(e) => { addFiles(e.target.files); e.target.value = '' }} />
              </label>
            )}
          </div>
          <span className="small muted">JPEG, PNG или WebP до 10 МБ. Геопозицию и другие данные камеры мы удаляем.</span>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="row">
          <button className="btn" disabled={busy || rating === 0}>{busy ? 'Сохраняем…' : editing ? 'Сохранить' : 'Опубликовать'}</button>
          {editing && (
            <button type="button" className="btn btn-ghost" onClick={onCancelEdit}>Отмена</button>
          )}
        </div>
      </div>
      <div className="stack review-form-wheel">
        <div className="field" style={{ display: 'block' }}>
          Аромат и ноты <span className="muted" style={{ fontWeight: 500 }}>· необязательно</span>
        </div>
        {wheel ? <FlavorPicker index={wheel} value={flavors} onChange={setFlavors} /> : <div className="skeleton" style={{ aspectRatio: '1' }} />}
      </div>
    </form>
  )
}

const MAX_PHOTOS = 3

/** Превью выбранного, ещё не загруженного файла. */
function FilePreview({ file }: { file: File }) {
  const url = useMemo(() => URL.createObjectURL(file), [file])
  useEffect(() => () => URL.revokeObjectURL(url), [url])
  return <img src={url} alt="" />
}
