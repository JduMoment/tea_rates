import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { PageHero } from '../components/PageHero'
import * as api from '../api'
import { useAuth } from '../auth/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { useCategories, useFlavorWheel, type WheelIndex } from '../hooks/useCatalog'
import { FlavorPicker } from '../components/FlavorWheel'
import type { Tea } from '../data/types'
import { SearchSelect } from '../components/SearchSelect'
import { TeaCard, TeaGridSkeleton } from '../components/TeaCard'
import { teasWord } from '../utils/format'

export function Teas() {
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const categories = useCategories()
  const category = params.get('category') ?? ''
  const shop = params.get('shop') ?? params.get('producer') ?? '' // producer — старый параметр
  const q = params.get('q') ?? ''
  const sortParam = params.get('sort')
  const sort: api.TeaSort = sortParam === 'reviews' || sortParam === 'title' || sortParam === 'price' ? sortParam : 'rating'
  const flavors = params.getAll('flavor')
  const flavorsKey = flavors.join(',')
  const wheel = useFlavorWheel()
  const [flavorOpen, setFlavorOpen] = useState(false)

  const teas = useAsync(
    () => api.getTeas({ category, shop, q, flavors: flavorsKey ? flavorsKey.split(',') : [], sort }),
    [category, shop, q, flavorsKey, sort],
  )
  // При поиске по вкусу: сначала чаи с совпавшими нотами, ниже — о вкусе которых ещё не писали
  const matched = flavors.length ? (teas.data?.filter((t) => t.flavorMatch) ?? []) : (teas.data ?? [])
  const undescribed = flavors.length ? (teas.data?.filter((t) => t.flavorMatch === null) ?? []) : []
  const shops = useAsync(() => api.getShops(), [])
  const cat = categories.bySlug(category)
  const shopInfo = shops.data?.find((s) => s.name === shop)

  function setFlavors(list: string[]) {
    const next = new URLSearchParams(params)
    next.delete('flavor')
    list.forEach((f) => next.append('flavor', f))
    setParams(next, { replace: true })
  }

  function set(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const addQuery = new URLSearchParams({ ...(category && { category }), ...(shop && { shop }) }).toString()
  const addHref = `/teas/new${addQuery ? `?${addQuery}` : ''}`

  return (
    <div className="page" style={{ gap: 32 }}>
      {shopInfo && (
        <nav className="small muted" aria-label="Навигация">
          <Link to={`/shops/${shopInfo.name}`}>← {shopInfo.title}</Link>
        </nav>
      )}
      <PageHero
        color={shopInfo ? cat?.color : undefined}
        eyebrow={shopInfo ? `Чаи магазина${cat ? ` · ${cat.plural.toLowerCase()}` : ''}` : 'Каталог'}
        title={shopInfo ? shopInfo.title : 'Все чаи'}
        lead={
          shopInfo
            ? 'Выберите чай, чтобы прочитать отзывы на него и посмотреть, почём он в других магазинах.'
            : 'Один и тот же чай продают разные магазины. На странице чая видно, где он лучше по отзывам и почём.'
        }
        stickers={[
          { text: 'Габа · 2 магазина', bg: 'var(--butter)', style: { right: '8%', top: 48 } },
          { text: 'мёд · персик · дым', bg: 'var(--peach)', style: { right: '16%', bottom: 48 } },
        ]}
      >
        <Link to={user ? addHref : '/login'} state={user ? undefined : { from: addHref }} className="btn">
          + Добавить {cat ? cat.name.toLowerCase() : 'чай'}
        </Link>
      </PageHero>

      <div className="toolbar">
        <div className="row" role="group" aria-label="Категория">
          <button type="button" className="chip" aria-pressed={!category} onClick={() => set('category', '')}>Все</button>
          {categories.list.map((c) => (
            <button key={c.slug} type="button" className="chip" aria-pressed={category === c.slug} onClick={() => set('category', c.slug)}>
              <span className="dot" style={{ background: c.ink }} aria-hidden="true" />
              {c.plural}
            </button>
          ))}
        </div>
        <div className="flavor-filter">
          <button type="button" className="chip" aria-expanded={flavorOpen} aria-pressed={flavors.length > 0} onClick={() => setFlavorOpen((o) => !o)}>
            По вкусу{flavors.length > 0 && ` · ${flavors.length}`} {flavorOpen ? '▴' : '▾'}
          </button>
          {wheel && <SelectedFlavors index={wheel} value={flavors} onChange={setFlavors} />}
        </div>
        {flavorOpen && wheel && (
          <div className="flavor-panel">
            <FlavorPicker index={wheel} value={flavors} onChange={setFlavors} max={wheel.all.length} groupSelect />
          </div>
        )}
        <div className="row">
          <label className="field" style={{ flex: '2 1 240px' }}>
            Поиск
            <input className="input" type="search" value={q} onChange={(e) => set('q', e.target.value)} placeholder="Название, магазин, нота вкуса" />
          </label>
          <label className="field" style={{ flex: '1 1 200px' }}>
            Магазин
            <SearchSelect
              options={[{ value: '', label: 'Все' }, ...(shops.data ?? []).map((s) => ({ value: s.name, label: s.title }))]}
              value={shop}
              onChange={(v) => set('shop', v)}
              loading={!shops.data}
            />
          </label>
          <label className="field" style={{ flex: '1 1 180px' }}>
            Сортировка
            <select className="select" value={sort} onChange={(e) => set('sort', e.target.value)}>
              <option value="rating">По оценке</option>
              <option value="reviews">По числу отзывов</option>
              <option value="price">Сначала дешёвые (за грамм)</option>
              <option value="title">По названию</option>
            </select>
          </label>
        </div>
      </div>

      <section aria-live="polite">
        {teas.error ? (
          <div className="empty">{teas.error}</div>
        ) : teas.loading && !teas.data ? (
          <TeaGridSkeleton count={8} />
        ) : matched.length || undescribed.length ? (
          <div className="stack" style={{ gap: 32 }}>
            {matched.length > 0 && (
              <div>
                <p className="small muted" style={{ marginBottom: 16 }}>
                  Найдено: {teasWord(matched.length)}
                  {flavors.length > 0 && ' — сначала те, где слышат больше выбранных нот'}
                </p>
                <div className="grid">
                  {matched.map((t) => <TeaCard key={t.id} tea={t} note={wheel && matchNote(wheel, t)} />)}
                </div>
              </div>
            )}
            {undescribed.length > 0 && (
              <div>
                <h3 style={{ marginBottom: 6 }}>О вкусе этих чаёв ещё не писали</h3>
                <p className="small muted" style={{ marginBottom: 16 }}>Может, в них тоже есть эти ноты — расскажите в отзыве.</p>
                <div className="grid">
                  {undescribed.map((t) => <TeaCard key={t.id} tea={t} />)}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="empty">
            {flavors.length > 0 ? 'Чаёв с этими нотами не нашлось. ' : 'Ничего не нашлось. '}
            Попробуйте убрать фильтры{user && (
              <> или <Link to={addHref} style={{ fontWeight: 700 }}>добавьте чай</Link></>
            )}.
          </div>
        )}
      </section>
    </div>
  )
}

/** «мёд · курага — в 57% отзывов» под карточкой при поиске по вкусу. */
function matchNote(index: WheelIndex, tea: Tea) {
  const m = tea.flavorMatch
  if (!m) return null
  const names = m.flavors.slice(0, 3).map((s) => index.flavor(s)?.flavor.title ?? s)
  const more = m.flavors.length > 3 ? ` и ещё ${m.flavors.length - 3}` : ''
  return `${names.join(' · ')}${more} — в ${Math.round(m.share * 100)}% отзывов`
}

/** Выбранные ноты кнопками «× убрать»; если выбрана вся группа — одна кнопка с её названием. */
function SelectedFlavors({ index, value, onChange }: { index: WheelIndex; value: string[]; onChange: (v: string[]) => void }) {
  if (!value.length) return null
  const selected = new Set(value)
  const items: { key: string; title: string; color: string; slugs: string[] }[] = []
  for (const g of index.wheel.groups) {
    const slugs = g.flavors.map((f) => f.slug)
    if (slugs.every((s) => selected.has(s))) items.push({ key: g.slug, title: g.title, color: g.color, slugs })
    else g.flavors.filter((f) => selected.has(f.slug)).forEach((f) => items.push({ key: f.slug, title: f.title, color: g.color, slugs: [f.slug] }))
  }
  return (
    <>
      {items.map((it) => (
        <button key={it.key} type="button" className="chip chip-sm" title="Убрать" onClick={() => onChange(value.filter((s) => !it.slugs.includes(s)))}>
          <span className="dot" style={{ background: it.color }} aria-hidden="true" />
          {it.title} ×
        </button>
      ))}
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => onChange([])}>Сбросить</button>
    </>
  )
}
