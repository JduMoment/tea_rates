import { useEffect, useState, type FormEvent } from 'react'
import { PageHero } from '../components/PageHero'
import { Link, useSearchParams } from 'react-router'
import * as api from '../api'
import { useAuth } from '../auth/AuthContext'
import { SHELF_STATUSES, type DiaryEntry, type ShelfItem, type ShelfStatus } from '../data/types'
import { useAsync } from '../hooks/useAsync'
import { suggestedParams } from '../utils/brewing'
import { CupIcon } from '../components/Icons'
import { LeafInput, Leaves } from '../components/Leaves'
import { Loading } from '../components/Layout'
import { SearchSelect } from '../components/SearchSelect'
import { BrewTimer } from '../components/BrewTimer'
import { fmtDate, plural } from '../utils/format'

const today = () => new Date().toISOString().slice(0, 10)

export function Diary() {
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const entries = useAsync(() => api.getDiary(), [user?.id])
  const shelf = useAsync(() => api.getShelf(), [user?.id])
  // ?add — открыть форму, ?add=<id> — ещё и выбрать чай (так возвращаемся после «Добавить чай»)
  const [open, setOpen] = useState(params.has('add'))
  const [formKey, setFormKey] = useState(0)
  const [presetTea, setPresetTea] = useState(params.get('add') ?? '')

  if (!user) return null

  function brew(teaId: number) {
    setPresetTea(String(teaId))
    setFormKey((k) => k + 1)
    setOpen(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="page" style={{ gap: 32 }}>
      <PageHero
        color="var(--lilac)"
        eyebrow={`Дневник · ${user.name}`}
        title="Чайный дневник"
        lead={
          entries.data?.length
            ? `${entries.data.length} ${plural(entries.data.length, 'запись', 'записи', 'записей')}. Что, как заваривали и как понравилось.`
            : 'Записывайте каждое чаепитие: что, как заваривали и как понравилось.'
        }
        stickers={[
          { text: '95 °C · 5 г', style: { right: '9%', top: 52 } },
          { text: '7 проливов', bg: 'var(--butter)', style: { right: '20%', bottom: 52 } },
        ]}
      >
        {!open && <button type="button" className="btn" onClick={() => setOpen(true)}>+ Новая запись</button>}
      </PageHero>

      {open && (
        <DiaryForm
          key={formKey}
          initialTeaId={presetTea}
          entries={entries.data ?? []}
          shelf={shelf.data ?? []}
          onCancel={() => {
            setOpen(false)
            setPresetTea('')
            setParams({}, { replace: true })
          }}
          onSaved={() => {
            setOpen(false)
            setPresetTea('')
            setParams({}, { replace: true })
            entries.reload()
            shelf.reload()
          }}
        />
      )}

      <Shelf items={shelf.data} onChanged={shelf.reload} onBrew={brew} />

      <section className="stack" aria-labelledby="entries-h">
        <h2 id="entries-h">Записи</h2>
        {entries.loading && !entries.data ? (
          <Loading />
        ) : entries.data?.length ? (
          <ol className="stack" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {entries.data.map((e) => (
              <li key={e.id} className="rank-row" style={{ alignItems: 'flex-start' }}>
                <span style={{ width: 72, height: 72, borderRadius: 20, background: e.tea.category.color, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}>
                  <CupIcon size={48} color={e.tea.category.ink} />
                </span>
                <div className="stack" style={{ flex: '999 1 320px', minWidth: 0, gap: 6 }}>
                  <span className="small muted">{fmtDate(e.date)}</span>
                  <Link to={`/teas/${e.tea.id}`} style={{ fontFamily: 'var(--display)', fontSize: 26, lineHeight: 1.1, textDecoration: 'none' }}>
                    {e.tea.title}
                  </Link>
                  <Link to={`/shops/${e.shop.name}`} className="small" style={{ fontWeight: 700 }}>{e.shop.title}</Link>
                  <div className="row" style={{ gap: 6 }}>
                    <span className="tag">{e.water} °C</span>
                    <span className="tag">{e.grams} г{e.volume ? ` на ${e.volume} мл` : ''}</span>
                    <span className="tag">{e.infusions} {plural(e.infusions, 'пролив', 'пролива', 'проливов')}</span>
                  </div>
                  {e.text && <p>{e.text}</p>}
                </div>
                <div className="stack" style={{ alignItems: 'flex-end', gap: 8 }}>
                  <Leaves value={e.rating} size={18} />
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => brew(e.tea.id)}>Заварить ещё</button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={async () => {
                      await api.deleteDiaryEntry(e.id)
                      entries.reload()
                    }}
                  >
                    Удалить
                  </button>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          !open && (
            <div className="empty stack" style={{ alignItems: 'center' }}>
              <CupIcon size={72} color="var(--accent)" />
              <p>В дневнике пока пусто.</p>
              <button type="button" className="btn" onClick={() => setOpen(true)}>Добавить первое чаепитие</button>
            </div>
          )
        )}
      </section>
    </div>
  )
}

// ---------- «Мои чаи» ----------

function Shelf({ items, onChanged, onBrew }: { items: ShelfItem[] | undefined; onChanged: () => void; onBrew: (teaId: number) => void }) {
  const [tab, setTab] = useState<ShelfStatus>('have')
  if (!items) return null
  const shown = items.filter((i) => i.status === tab)
  return (
    <section className="stack" aria-labelledby="shelf-h">
      <div className="section-head">
        <h2 id="shelf-h">Мои чаи</h2>
        <span className="small muted">Добавляйте со страницы чая: «Хочу попробовать», «Есть дома»</span>
      </div>
      <div className="row" style={{ gap: 6 }} role="tablist" aria-label="Статус">
        {SHELF_STATUSES.map((s) => (
          <button key={s.id} type="button" role="tab" className="chip" aria-selected={tab === s.id} aria-pressed={tab === s.id} onClick={() => setTab(s.id)}>
            {s.label} · {items.filter((i) => i.status === s.id).length}
          </button>
        ))}
      </div>
      {shown.length ? (
        <ul className="shelf-list">
          {shown.map((i) => (
            <li key={i.tea.id} className="shelf-item">
              <span className="dot" style={{ background: i.tea.category.ink }} aria-hidden="true" />
              <Link to={`/teas/${i.tea.id}`} className="shelf-title">{i.tea.title}</Link>
              <span className="small muted">{i.tea.category.name}</span>
              <span className="row" style={{ gap: 6, marginLeft: 'auto' }}>
                {i.status !== 'want' && (
                  <button type="button" className="btn btn-sm" onClick={() => onBrew(i.tea.id)}>Заварить</button>
                )}
                <select
                  className="select select-sm"
                  aria-label={`Статус: ${i.tea.title}`}
                  value={i.status}
                  onChange={async (e) => {
                    const v = e.target.value
                    if (v === 'remove') await api.removeFromShelf(i.tea.id)
                    else await api.putShelf(i.tea.id, v as ShelfStatus)
                    onChanged()
                  }}
                >
                  {SHELF_STATUSES.map((s) => (
                    <option key={s.id} value={s.id}>{s.label}</option>
                  ))}
                  <option value="remove">Убрать из моих чаёв</option>
                </select>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="small muted">
          {tab === 'want' ? 'Отмечайте на странице чая «Хочу попробовать» — список соберётся здесь.' : tab === 'have' ? 'Чаи, которые вы записываете в дневник, попадают сюда сами.' : 'Пока ничего не закончилось.'}
        </p>
      )}
    </section>
  )
}

// ---------- форма записи ----------

interface Draft {
  teaId: number
  shopId: number
  date: string
  rating: number
  water: number
  grams: number
  volume: string
  infusions: number
  text: string
}

const DRAFT_KEY = 'tea-diary-draft'

function loadDraft(): Partial<Draft> {
  try {
    return JSON.parse(localStorage.getItem(DRAFT_KEY) ?? '{}') as Partial<Draft>
  } catch {
    return {}
  }
}
function saveDraft(d: Draft) {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(d))
  } catch {
    /* приватный режим и т.п. — без черновика */
  }
}
function clearDraft() {
  try {
    localStorage.removeItem(DRAFT_KEY)
  } catch {
    /* нечего чистить */
  }
}

function DiaryForm({
  initialTeaId,
  entries,
  shelf,
  onSaved,
  onCancel,
}: {
  initialTeaId: string
  entries: DiaryEntry[]
  shelf: ShelfItem[]
  onSaved: () => void
  onCancel: () => void
}) {
  const { user } = useAuth()
  const teas = useAsync(() => api.getTeas({ sort: 'title' }), [])
  // Черновик: всё, что успели ввести, переживает уход со страницы (например, в «Добавить чай»)
  const [draft] = useState(loadDraft)
  const restored = Object.keys(draft).length > 0
  // Пришли с готовым чаем (?add=<id>, «Заварить ещё») и без черновика — сразу прошлые параметры этого чая
  const [last] = useState(() => (!restored && Number(initialTeaId) ? entries.find((e) => e.teaId === Number(initialTeaId)) : undefined))
  const [teaId, setTeaIdRaw] = useState(Number(initialTeaId) || draft.teaId || 0)
  const [chosenShop, setShopId] = useState(draft.shopId ?? last?.shopId ?? 0)
  const [date, setDate] = useState(draft.date ?? today())
  const [rating, setRating] = useState(draft.rating ?? 0)
  const [water, setWater] = useState(draft.water ?? last?.water ?? 90)
  const [grams, setGrams] = useState(draft.grams ?? last?.grams ?? 5)
  const [volume, setVolume] = useState(draft.volume ?? (last?.volume ? String(last.volume) : ''))
  const [infusions, setInfusions] = useState(draft.infusions ?? last?.infusions ?? 5)
  const [text, setText] = useState(draft.text ?? '')
  const [hint, setHint] = useState<string | null>(last ? `Как в прошлый раз (${fmtDate(last.date)})` : null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    saveDraft({ teaId, shopId: chosenShop, date, rating, water, grams, volume, infusions, text })
  }, [teaId, chosenShop, date, rating, water, grams, volume, infusions, text])

  function applyParams(p: { water: number; grams: number; volume: number | null; infusions: number }, why: string) {
    setWater(p.water)
    setGrams(p.grams)
    setVolume(p.volume ? String(p.volume) : '')
    setInfusions(p.infusions)
    setHint(why)
  }

  /** Сменили чай: если уже заваривали его — подставляем прошлые параметры. */
  function setTeaId(id: number) {
    setTeaIdRaw(id)
    const last = entries.find((e) => e.teaId === id)
    if (last) applyParams(last, `Как в прошлый раз (${fmtDate(last.date)})`)
    else setHint(null)
  }

  async function useCommon() {
    if (!teaId) return setError('Сначала выберите чай')
    try {
      const b = await api.getBrewing(teaId)
      const why = b.liked ? 'Как заваривают те, кому чай понравился' : b.community ? 'Как обычно заваривают этот чай' : `Типично для вида «${b.category.toLowerCase()}»`
      applyParams(suggestedParams(b), why)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!user) return
    if (!teaId) return setError('Выберите чай')
    if (!shopId) return setError('Выберите магазин, где купили чай')
    if (!rating) return setError('Поставьте оценку')
    setBusy(true)
    setError(null)
    try {
      await api.addDiaryEntry({ teaId, shopId, date, rating, water, grams, volume: volume ? Number(volume) : null, infusions, text: text.trim() })
      clearDraft()
      onSaved()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const tea = teas.data?.find((t) => t.id === teaId)
  const offers = tea?.offers ?? []
  // Если чай продаётся в одном магазине — выбирать нечего
  const shopId = offers.some((o) => o.shopId === chosenShop) ? chosenShop : offers.length === 1 ? offers[0].shopId : 0
  // Чаи из шкафа — первыми: «есть дома» выше всего
  const rank = new Map(shelf.map((i) => [i.tea.id, i.status === 'have' ? 0 : i.status === 'want' ? 1 : 2]))
  const status = new Map(shelf.map((i) => [i.tea.id, i.statusLabel]))
  const teaOptions = [...(teas.data ?? [])]
    .sort((a, b) => (rank.get(a.id) ?? 3) - (rank.get(b.id) ?? 3))
    .map((t) => ({
      value: t.id,
      label: t.title,
      hint: [status.get(t.id), t.category.name, t.offers.map((o) => o.shop.title).join(', ')].filter(Boolean).join(' · '),
    }))

  return (
    <form className="card stack" onSubmit={submit} style={{ gap: 20 }}>
      <div className="row between">
        <h2 style={{ fontSize: 30 }}>Новая запись</h2>
        {restored && <span className="small muted">Черновик восстановлен</span>}
      </div>
      <div className="row" style={{ alignItems: 'flex-end' }}>
        <label className="field" style={{ flex: '3 1 300px' }}>
          Чай
          <SearchSelect
            options={teaOptions}
            value={teaId}
            onChange={setTeaId}
            placeholder="Выберите чай…"
            loading={!teas.data}
            notFound="Такого чая в каталоге нет"
            footer={(q) => (
              <Link to={`/teas/new?${new URLSearchParams({ next: 'diary', ...(q && { title: q }) })}`} style={{ fontWeight: 700 }}>
                + Нет нужного? Добавить {q ? `«${q}»` : 'чай'} в каталог
              </Link>
            )}
          />
        </label>
        <label className="field" style={{ flex: '2 1 220px' }}>
          Где купили
          <SearchSelect
            options={offers.map((o) => ({ value: o.shopId, label: o.shop.title }))}
            value={shopId}
            onChange={setShopId}
            placeholder={teaId ? 'Выберите магазин…' : 'Сначала выберите чай'}
            disabled={!offers.length}
          />
        </label>
        <label className="field" style={{ flex: '1 1 160px' }}>
          Дата
          <input className="input" type="date" value={date} max={today()} onChange={(e) => setDate(e.target.value)} />
        </label>
      </div>
      <div className="row" style={{ alignItems: 'flex-end' }}>
        <label className="field" style={{ flex: '1 1 110px' }}>
          Вода, °C
          <input className="input" type="number" min={40} max={100} value={water} onChange={(e) => setWater(Number(e.target.value))} />
        </label>
        <label className="field" style={{ flex: '1 1 110px' }}>
          Граммы
          <input className="input" type="number" min={0.5} max={50} step={0.5} value={grams} onChange={(e) => setGrams(Number(e.target.value))} />
        </label>
        <label className="field" style={{ flex: '1 1 130px' }}>
          Объём посуды, мл
          <input className="input" type="number" min={20} max={3000} step={10} placeholder="100" value={volume} onChange={(e) => setVolume(e.target.value)} />
        </label>
        <label className="field" style={{ flex: '1 1 110px' }}>
          Проливы
          <input className="input" type="number" min={1} max={50} value={infusions} onChange={(e) => setInfusions(Number(e.target.value))} />
        </label>
      </div>
      <div className="row" style={{ gap: 10 }}>
        <button type="button" className="btn btn-ghost btn-sm" onClick={useCommon} disabled={!teaId}>
          Подставить, как обычно заваривают
        </button>
        {hint && <span className="small muted">{hint}</span>}
      </div>
      <BrewTimer category={tea?.category.slug} onDone={(n) => setInfusions(n)} />
      <LeafInput value={rating} onChange={setRating} name="diary-rating" />
      <label className="field">
        Заметки
        <textarea className="textarea" value={text} onChange={(e) => setText(e.target.value)} placeholder="Посуда, настроение, как менялся вкус…" />
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row">
        <button className="btn" disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить'}</button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => {
            clearDraft()
            onCancel()
          }}
        >
          Отмена
        </button>
      </div>
    </form>
  )
}
