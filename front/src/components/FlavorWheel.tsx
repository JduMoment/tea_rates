/**
 * Колесо вкусов: в центре — группы, внешнее кольцо — дескрипторы.
 * Всё по часовой стрелке от «12 часов», в порядке из GET /api/flavors.
 *
 * Базовых вкусов на колесе нет: у соседних нот они чередуются, и кольцо вкусов рассыпалось
 * на два десятка цветных обрывков. Вкус ноты — в подсказке при наведении, сводка — под колесом.
 *
 * Пользователь выбирает только дескрипторы; группа и вкус подсвечиваются сами.
 * FlavorPicker — выбор в форме отзыва, FlavorProfileView — профиль чая по отзывам.
 */
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import type { FlavorProfile } from '../data/types'
import type { FlavorEntry, WheelIndex } from '../hooks/useCatalog'
import { textOn } from '../utils/color'

// ---------- геометрия ----------

// Подписи нот — внутри ячеек внешнего кольца, поэтому оно широкое и доходит почти до края.
// Чем дальше кольцо от центра, тем шире сектор каждой ноты: и текст влезает, и попасть легче.
const R = {
  group: 190, // группы — от самого центра
  groupLabel: 122, // подписи групп ближе к краю: у центра секторы слишком узкие
  flavor: 400, // внешнее — дескрипторы с подписями внутри (влезает «свежескошенная трава»)
}
const VIEW = R.flavor + 4

/** Точка на окружности: угол в градусах по часовой от «12 часов». */
function point(r: number, deg: number): [number, number] {
  const rad = (deg * Math.PI) / 180
  return [r * Math.sin(rad), -r * Math.cos(rad)]
}

/** Кольцевой сектор между радиусами r0..r1 и углами a0..a1. */
function sector(r0: number, r1: number, a0: number, a1: number) {
  const large = a1 - a0 > 180 ? 1 : 0
  const [x0, y0] = point(r1, a0)
  const [x1, y1] = point(r1, a1)
  const [x2, y2] = point(r0, a1)
  const [x3, y3] = point(r0, a0)
  return `M${x0},${y0} A${r1},${r1} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${r0},${r0} 0 ${large} 0 ${x3},${y3} Z`
}

/** Подпись вдоль радиуса; на левой половине переворачиваем, чтобы читалась слева направо. */
function radial(r: number, deg: number, anchor: 'outer' | 'middle') {
  const [x, y] = point(r, deg)
  const left = deg % 360 > 180
  const rotate = left ? deg + 90 : deg - 90
  const textAnchor = anchor === 'middle' ? 'middle' : left ? 'end' : 'start'
  return { x, y, transform: `rotate(${rotate} ${x} ${y})`, textAnchor } as const
}


interface Layout {
  step: number
  flavors: { slug: string; title: string; taste: string; color: string; a0: number; a1: number }[]
  groups: { slug: string; title: string; color: string; a0: number; a1: number }[]
}

function layout(index: WheelIndex): Layout {
  const step = 360 / index.all.length
  const flavors: Layout['flavors'] = []
  const groups: Layout['groups'] = []
  let i = 0
  for (const g of index.wheel.groups) {
    const start = i * step
    for (const f of g.flavors) {
      const a0 = i * step
      const a1 = a0 + step
      const taste = index.taste(f.taste)?.title ?? ''
      flavors.push({ slug: f.slug, title: f.title, taste, color: g.color, a0, a1 })
      i++
    }
    groups.push({ slug: g.slug, title: g.title, color: g.color, a0: start, a1: i * step })
  }
  return { step, flavors, groups }
}

// ---------- само колесо ----------

interface WheelProps {
  index: WheelIndex
  /** Насколько ярко рисовать дескриптор / группу: 0–1. */
  flavorLevel: (slug: string) => number
  groupLevel: (slug: string) => number
  /** Выделенные дескрипторы — жирная подпись. */
  marked: (slug: string) => boolean
  /** Подсказка при наведении на дескриптор. */
  flavorHint?: (slug: string, title: string) => string
  onFlavorClick?: (slug: string) => void
  onGroupClick?: (slug: string) => void
  focusedGroup?: string | null
  label: string
}

export function FlavorWheel({
  index,
  flavorLevel,
  groupLevel,
  marked,
  flavorHint,
  onFlavorClick,
  onGroupClick,
  focusedGroup,
  label,
}: WheelProps) {
  const geo = useMemo(() => layout(index), [index])
  const opacity = (level: number) => 0.14 + 0.86 * level

  return (
    <svg className="wheel" viewBox={`${-VIEW} ${-VIEW} ${VIEW * 2} ${VIEW * 2}`} role="img" aria-label={label}>
      {/* группы */}
      {geo.groups.map((g) => {
        const mid = (g.a0 + g.a1) / 2
        const level = groupLevel(g.slug)
        const focused = focusedGroup === g.slug
        const label = radial(R.groupLabel, mid, 'middle')
        // Длинное название из двух слов — в две строки, иначе не влезет в кольцо
        const lines = g.title.length > 12 && g.title.includes(' ') ? g.title.split(/ (.*)/s, 2) : [g.title]
        return (
          <g
            key={g.slug}
            className={onGroupClick ? 'wheel-hit' : undefined}
            onClick={onGroupClick ? () => onGroupClick(g.slug) : undefined}
          >
            <path
              d={sector(0, R.group, g.a0, g.a1)}
              fill={g.color}
              opacity={opacity(level)}
              stroke={focused ? '#22301a' : '#fff'}
              strokeWidth={focused ? 4 : 2}
            >
              <title>{g.title}</title>
            </path>
            <text
              {...label}
              dominantBaseline="central"
              fontSize={g.a1 - g.a0 < 10 ? 12 : 14}
              fontWeight={700}
              fill={textOn(g.color, opacity(level))}
              opacity={level > 0.3 ? 1 : 0.6}
              pointerEvents="none"
            >
              {lines.map((line, i) => (
                <tspan key={i} x={label.x} dy={i === 0 ? `${-(lines.length - 1) * 0.6}em` : '1.2em'}>
                  {line.toUpperCase()}
                </tspan>
              ))}
            </text>
          </g>
        )
      })}

      {/* дескрипторы */}
      {geo.flavors.map((f) => {
        const mid = (f.a0 + f.a1) / 2
        const level = flavorLevel(f.slug)
        const isMarked = marked(f.slug)
        return (
          <g
            key={f.slug}
            className={onFlavorClick ? 'wheel-hit wheel-flavor' : undefined}
            onClick={onFlavorClick ? () => onFlavorClick(f.slug) : undefined}
          >
            <title>
              {flavorHint ? flavorHint(f.slug, f.title) : f.title}
              {f.taste && ` · ${f.taste.toLowerCase()}`}
            </title>
            <path
              d={sector(R.group + 2, R.flavor, f.a0, f.a1)}
              fill={f.color}
              opacity={opacity(level)}
              stroke="#fff"
              strokeWidth={0.75}
            />
            {/* Подпись внутри ячейки, вдоль радиуса, по центру кольца — там ячейка шире */}
            <text
              {...radial((R.group + R.flavor) / 2, mid, 'middle')}
              dominantBaseline="central"
              fontSize={16}
              fontWeight={isMarked ? 800 : 600}
              fill={textOn(f.color, opacity(level))}
              opacity={isMarked || level > 0.3 ? 1 : 0.6}
              pointerEvents="none"
            >
              {f.title}
            </text>
          </g>
        )
      })}

    </svg>
  )
}

// ---------- выбор в отзыве ----------

export function FlavorPicker({
  index,
  value,
  onChange,
  max = 7,
  groupSelect = false,
}: {
  index: WheelIndex
  value: string[]
  onChange: (v: string[]) => void
  max?: number
  /** Клик по группе выбирает все её ноты (поиск по вкусу), а не раскрывает их списком (отзыв). */
  groupSelect?: boolean
}) {
  const [focused, setFocused] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const selected = new Set(value)
  const groups = new Set(value.map((s) => index.flavor(s)?.group.slug))
  const full = value.length >= max
  // Попытка выбрать ноту сверх лимита — показываем уведомление, оно гаснет само
  const [overLimit, setOverLimit] = useState(false)
  useEffect(() => {
    if (!overLimit) return
    const t = setTimeout(() => setOverLimit(false), 4000)
    return () => clearTimeout(t)
  }, [overLimit])

  function toggle(slug: string) {
    if (selected.has(slug)) {
      setOverLimit(false)
      onChange(value.filter((s) => s !== slug))
    } else if (full) setOverLimit(true)
    else onChange([...value, slug])
  }

  /** Вся группа выбрана — снять её; иначе — добрать недостающие ноты. */
  function toggleGroup(slug: string) {
    const slugs = index.group(slug)?.flavors.map((f) => f.slug) ?? []
    const all = slugs.every((s) => selected.has(s))
    onChange(all ? value.filter((s) => !slugs.includes(s)) : [...value, ...slugs.filter((s) => !selected.has(s))].slice(0, max))
  }
  const groupFull = (slug: string) => index.group(slug)?.flavors.every((f) => selected.has(f.slug)) ?? false
  const onGroup = (slug: string) => (groupSelect ? toggleGroup(slug) : setFocused((cur) => (cur === slug ? null : slug)))

  const needle = q.trim().toLowerCase()
  const found = needle ? index.all.filter((e) => e.flavor.title.includes(needle)).slice(0, 12) : []
  const group = focused ? index.group(focused) : undefined
  // Под колесом — найденные ноты или ноты выбранной группы
  const chips: FlavorEntry[] = needle ? found : (group?.flavors.map((f) => index.flavor(f.slug)!) ?? [])

  return (
    <div className="stack" style={{ gap: 12 }}>
      <FlavorWheel
        index={index}
        label="Колесо вкусов: нажмите на ноту, чтобы отметить её"
        // Изначально всё приглушено, как после выбора: ярко горит только выбранное и открытая группа
        flavorLevel={(s) => (selected.has(s) ? 1 : focused && index.flavor(s)?.group.slug === focused ? 0.6 : 0.25)}
        groupLevel={(s) => (groups.has(s) || focused === s ? 1 : 0.35)}
        marked={(s) => selected.has(s)}
        flavorHint={(s, title) => (selected.has(s) ? `${title} — убрать` : title)}
        onFlavorClick={toggle}
        onGroupClick={onGroup}
        focusedGroup={focused}
      />

      <div role="status" aria-live="polite">
        {overLimit && (
          <p className="notice small">Можно отметить не больше {max} нот. Уберите одну, чтобы выбрать другую.</p>
        )}
      </div>

      <input
        className="input"
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Поиск ноты: персик, мёд, дым…"
        aria-label="Поиск ноты"
      />

      {/* Группы кнопками — для телефона и клавиатуры, где по тонким секторам не попасть */}
      {!needle && (
        <div className="row" style={{ gap: 6 }} role="group" aria-label="Группы вкусов">
          {index.wheel.groups.map((g) => (
            <button key={g.slug} type="button" className="chip chip-sm" aria-pressed={groupSelect ? groupFull(g.slug) : focused === g.slug} onClick={() => onGroup(g.slug)}>
              <span className="dot" style={{ background: g.color }} aria-hidden="true" />
              {g.title}
            </button>
          ))}
        </div>
      )}

      {chips.length > 0 && (
        <div className="row" style={{ gap: 6 }} role="group" aria-label="Ноты">
          {chips.map((e) => (
            <button
              key={e.flavor.slug}
              type="button"
              className="chip chip-sm"
              aria-pressed={selected.has(e.flavor.slug)}
              onClick={() => toggle(e.flavor.slug)}
            >
              <span className="dot" style={{ background: e.group.color }} aria-hidden="true" />
              {e.flavor.title}
              {needle && <span className="muted"> · {e.group.title.toLowerCase()}</span>}
            </button>
          ))}
        </div>
      )}
      {needle && found.length === 0 && <span className="small muted">Такой ноты на колесе нет.</span>}
    </div>
  )
}

// ---------- профиль чая ----------

const pct = (share: number) => `${Math.round(share * 100)}%`

export function FlavorProfileView({
  index,
  profile,
  label = 'Вкусовой профиль чая по отзывам',
  empty = 'Пока никто не отметил ноты вкуса. Оставьте отзыв — и здесь появится колесо.',
}: {
  index: WheelIndex
  profile: FlavorProfile
  label?: string
  empty?: ReactNode
}) {
  const flavors = new Map(profile.flavors.map((s) => [s.slug, s]))
  const groups = new Map(profile.groups.map((s) => [s.slug, s]))
  // Яркость — относительно самой частой ноты, иначе при 10 отзывах всё было бы бледным
  const norm = (m: Map<string, { share: number }>) => {
    const top = Math.max(0, ...[...m.values()].map((s) => s.share))
    return (slug: string) => (top ? (m.get(slug)?.share ?? 0) / top : 0)
  }

  if (profile.reviews === 0) {
    return <div className="empty">{empty}</div>
  }

  return (
    <div className="profile-grid">
      <FlavorWheel
        index={index}
        label={label}
        flavorLevel={norm(flavors)}
        groupLevel={norm(groups)}
        marked={(s) => flavors.has(s)}
        flavorHint={(s, title) => {
          const x = flavors.get(s)
          return x ? `${title}: ${x.count} из ${profile.reviews} (${pct(x.share)})` : title
        }}
      />
      <div className="profile-stats">
        <p className="small muted" style={{ gridColumn: '1 / -1' }}>
          По {profile.reviews} {profile.reviews === 1 ? 'отзыву' : 'отзывам'} с отмеченными нотами. Процент — сколько из них упомянули ноту.
        </p>
        <div className="stack" style={{ gap: 10 }}>
          <h3 style={{ fontSize: 22 }}>Вкус</h3>
          {profile.tastes.map((s) => {
            const t = index.taste(s.slug)
            return t && <ShareBar key={s.slug} title={t.title} color={t.color} share={s.share} />
          })}
        </div>
        <div className="stack" style={{ gap: 10 }}>
          <h3 style={{ fontSize: 22 }}>Чаще всего слышат</h3>
          {profile.groups.slice(0, 5).map((s) => {
            const g = index.group(s.slug)
            return g && <ShareBar key={s.slug} title={g.title} color={g.color} share={s.share} />
          })}
        </div>
        <div className="row" style={{ gap: 6, alignContent: 'flex-start' }}>
          {profile.flavors.slice(0, 10).map((s) => {
            const e = index.flavor(s.slug)
            return (
              e && (
                <span key={s.slug} className="tag" style={{ background: e.group.color, color: textOn(e.group.color) }}>
                  {e.flavor.title} · {pct(s.share)}
                </span>
              )
            )
          })}
        </div>
      </div>
    </div>
  )
}

function ShareBar({ title, color, share }: { title: string; color: string; share: number }) {
  return (
    <div className="stack" style={{ gap: 4 }}>
      <span className="row between small">
        <strong>{title}</strong>
        <span className="muted">{pct(share)}</span>
      </span>
      <span className="bar" aria-hidden="true">
        <span style={{ width: pct(share), background: color }} />
      </span>
    </div>
  )
}

/** Ноты отзыва цветными тегами. */
export function FlavorTags({ index, slugs }: { index: WheelIndex | undefined; slugs: string[] }) {
  if (!index || slugs.length === 0) return null
  return (
    <div className="row" style={{ gap: 6 }}>
      {slugs.map((s) => {
        const e = index.flavor(s)
        return (
          e && (
            <span key={s} className="tag" style={{ background: e.group.color, color: textOn(e.group.color) }} title={`${e.group.title} · ${e.taste.title.toLowerCase()}`}>
              {e.flavor.title}
            </span>
          )
        )
      })}
    </div>
  )
}
