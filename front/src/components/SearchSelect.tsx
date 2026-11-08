import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'

export interface SelectOption<V> {
  value: V
  label: string
  /** Серая подпись под названием; по ней тоже ищем (вид чая, магазины…). */
  hint?: string
}

/** Для поиска: регистр и ё/е не важны. */
const norm = (s: string) => s.toLocaleLowerCase('ru').replaceAll('ё', 'е')

/**
 * Выпадающий список с поиском по вариантам — вместо <select>, когда вариантов много.
 * Фокус — список открыт, вводим часть названия — он сужается. Стрелки, Enter, Esc работают.
 */
export function SearchSelect<V extends string | number>({
  options,
  value,
  onChange,
  placeholder = 'Выберите…',
  disabled = false,
  loading = false,
  notFound = 'Ничего не нашлось',
  footer,
  'aria-label': ariaLabel,
}: {
  options: SelectOption<V>[]
  value: V
  onChange: (value: V) => void
  placeholder?: string
  disabled?: boolean
  loading?: boolean
  notFound?: string
  /** Под списком, всегда видно (например, «Добавить чай»). Получает введённый текст. */
  footer?: (query: string) => ReactNode
  'aria-label'?: string
}) {
  const listId = useId()
  const listRef = useRef<HTMLUListElement>(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)

  const selected = options.find((o) => o.value === value)
  const shown = useMemo(() => {
    const words = norm(query).split(/\s+/).filter(Boolean)
    if (!words.length) return options
    return options.filter((o) => {
      const text = norm(`${o.label} ${o.hint ?? ''}`)
      return words.every((w) => text.includes(w))
    })
  }, [options, query])

  // Подсвеченный вариант всегда виден при листании стрелками
  useEffect(() => {
    if (open) listRef.current?.children[active]?.scrollIntoView({ block: 'nearest' })
  }, [active, open])

  function openList() {
    if (disabled) return
    setQuery('')
    setActive(Math.max(0, options.findIndex((o) => o.value === value)))
    setOpen(true)
  }

  function choose(option: SelectOption<V>) {
    onChange(option.value)
    setOpen(false)
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        e.preventDefault()
        openList()
      }
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => Math.min(i + 1, shown.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault() // не отправлять форму
      if (shown[active]) choose(shown[active])
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setOpen(false)
    }
  }

  return (
    <div className="search-select">
      <input
        className="input"
        role="combobox"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && shown[active] ? `${listId}-${active}` : undefined}
        autoComplete="off"
        disabled={disabled}
        // Закрыт — показываем выбранное; открыт — то, что вводят, а выбранное — подсказкой
        value={open ? query : (selected?.label ?? '')}
        placeholder={open ? (selected?.label ?? 'Начните вводить название') : loading ? 'Загружаем…' : placeholder}
        onFocus={openList}
        onClick={() => !open && openList()}
        onBlur={() => setOpen(false)}
        onChange={(e) => {
          setQuery(e.target.value)
          setActive(0)
          setOpen(true)
        }}
        onKeyDown={onKeyDown}
      />
      <span className="search-select-chevron" aria-hidden="true">▾</span>
      {open && (
        // mousedown не уводит фокус из поля — иначе список закроется раньше клика
        <div className="search-select-pop" onMouseDown={(e) => e.preventDefault()}>
          <ul id={listId} ref={listRef} role="listbox" className="search-select-list" hidden={shown.length === 0}>
            {shown.map((o, i) => (
              <li
                key={String(o.value)}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={o.value === value}
                className={i === active ? 'active' : undefined}
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(o)}
              >
                <span>{o.label}</span>
                {o.hint && <span className="small muted">{o.hint}</span>}
              </li>
            ))}
          </ul>
          {shown.length === 0 && <p className="search-select-empty small muted">{loading ? 'Загружаем…' : notFound}</p>}
          {footer && <div className="search-select-footer">{footer(query.trim())}</div>}
        </div>
      )}
    </div>
  )
}
