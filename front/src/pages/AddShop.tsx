import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import * as api from '../api'
import type { ShopCheck } from '../data/types'
import { PageHero } from '../components/PageHero'
import { ImageField } from '../components/CatalogImage'

/** Задержка проверки на дубли: не дёргаем сервер на каждую букву. */
function useDebounced<T>(value: T, ms = 400): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

/** Добавить магазин: /shops/new?title=…&back=/teas/new?…
 *  back — куда вернуться после создания (туда допишется ?shop=<name>, и магазин выберется сам). */
export function AddShop() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const back = params.get('back')
  const [title, setTitle] = useState(params.get('title') ?? '')
  const [site, setSite] = useState('')
  const [city, setCity] = useState('')
  const [country, setCountry] = useState('Россия')
  const [description, setDescription] = useState('')
  const [logo, setLogo] = useState<File | null>(null)
  const [check, setCheck] = useState<ShopCheck | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Проверка на дубли по мере ввода: тот же сайт — нельзя, похожее название — предупреждаем
  const qTitle = useDebounced(title.trim())
  const qSite = useDebounced(site.trim())
  useEffect(() => {
    if (!qTitle && !qSite) return
    let alive = true
    api
      .checkShop(qTitle, qSite)
      .then((c) => alive && setCheck(c))
      .catch(() => alive && setCheck(null))
    return () => {
      alive = false
    }
  }, [qTitle, qSite])
  const shown = qTitle || qSite ? check : null

  function returnWith(name: string) {
    if (back?.startsWith('/')) {
      const [path, hash = ''] = back.split('#')
      navigate(`${path}${path.includes('?') ? '&' : '?'}shop=${encodeURIComponent(name)}${hash ? `#${hash}` : ''}`)
    } else navigate(`/shops/${name}`)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (shown?.sameSite) return setError(`Этот магазин уже есть — «${shown.sameSite.title}»`)
    setBusy(true)
    setError(null)
    try {
      const shop = await api.createShop({ title, site, city, country, description: description || null })
      // Логотип не загрузился — магазин всё равно создан; загрузить можно на его странице
      if (logo) await api.uploadShopLogo(shop.id, logo).catch(() => undefined)
      returnWith(shop.name)
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <div className="page" style={{ gap: 32 }}>
      <PageHero
        color="var(--butter)"
        eyebrow="Магазины"
        title="Добавить магазин"
        lead="Один магазин — одна карточка. Мы сверяем сайт и название с теми, что уже есть, чтобы не было дублей."
      />

      <form className="card stack add-tea" onSubmit={submit} style={{ gap: 20 }}>
        <label className="field">
          Название
          <input className="input" required maxLength={128} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Как магазин называет себя на сайте" />
        </label>

        <label className="field">
          Сайт <span className="muted" style={{ fontWeight: 500 }}>обязательно — по нему узнаём магазин</span>
          <input
            className="input"
            required
            inputMode="url"
            maxLength={512}
            value={site}
            onChange={(e) => setSite(e.target.value)}
            placeholder="Адрес сайта или страницы в соцсети"
          />
        </label>
        {qSite && shown?.siteError && <p className="error" role="alert">{shown.siteError}</p>}

        {shown?.sameSite && (
          <div className="card stack dup-block dup-block-stop" role="alert">
            <strong>Этот магазин уже есть в каталоге</strong>
            <span>
              Сайт {shown.siteKey} уже у магазина{' '}
              <Link to={`/shops/${shown.sameSite.name}`} style={{ fontWeight: 700 }}>«{shown.sameSite.title}»</Link>.
            </span>
            {back && (
              <button type="button" className="btn btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => returnWith(shown.sameSite!.name)}>
                Выбрать его
              </button>
            )}
          </div>
        )}

        {shown && !shown.sameSite && shown.similar.length > 0 && (
          <div className="card stack dup-block" role="status">
            <strong>Похоже, такой магазин уже есть:</strong>
            {shown.similar.map((s) => (
              <span key={s.id} className="row" style={{ gap: 10 }}>
                <Link to={`/shops/${s.name}`} style={{ fontWeight: 700 }}>{s.title}</Link>
                {back && (
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => returnWith(s.name)}>Это он</button>
                )}
              </span>
            ))}
            <span className="small muted">Если это другой магазин с похожим названием — просто продолжайте.</span>
          </div>
        )}

        <div className="row">
          <label className="field" style={{ flex: '2 1 200px' }}>
            Город
            <input className="input" required maxLength={64} value={city} onChange={(e) => setCity(e.target.value)} placeholder="Москва" />
          </label>
          <label className="field" style={{ flex: '1 1 160px' }}>
            Страна
            <input className="input" required maxLength={64} value={country} onChange={(e) => setCountry(e.target.value)} />
          </label>
        </div>

        <label className="field">
          Описание <span className="muted" style={{ fontWeight: 500 }}>необязательно</span>
          <textarea className="textarea" maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Чем известен, что привозит" />
        </label>

        <ImageField label="Логотип" hint="Лучше квадратный, можно с прозрачным фоном. JPEG, PNG или WebP до 10 МБ." file={logo} onChange={setLogo} />

        {error && <p className="error" role="alert">{error}</p>}
        <div className="row">
          <button className="btn" disabled={busy || Boolean(shown?.sameSite) || !title.trim() || !site.trim() || !city.trim()}>
            {busy ? 'Добавляем…' : 'Добавить магазин'}
          </button>
          <Link to={back?.startsWith('/') ? back : '/shops'} className="btn btn-ghost">Отмена</Link>
        </div>
      </form>
    </div>
  )
}
