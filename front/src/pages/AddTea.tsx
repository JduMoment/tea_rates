import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import * as api from '../api'
import { PageHero } from '../components/PageHero'
import { OfferFields } from '../components/OfferFields'
import { ImageField } from '../components/CatalogImage'
import { emptyOffer, offerInput } from '../utils/offer'
import { useAsync } from '../hooks/useAsync'
import { useCategories } from '../hooks/useCatalog'

/** Добавить чай в каталог: /teas/new?category=gaba&shop=art-of-tea&title=…
 *  Все параметры — необязательные подсказки. next=diary — пришли из дневника: после добавления
 *  возвращаемся туда с уже выбранным новым чаем. */
export function AddTea() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const categories = useCategories()
  const shops = useAsync(() => api.getShops(), [])
  const [category, setCategory] = useState(params.get('category') ?? '')
  const [title, setTitle] = useState(params.get('title') ?? '')
  const fromDiary = params.get('next') === 'diary'
  const [region, setRegion] = useState('')
  const [description, setDescription] = useState('')
  const [offer, setOffer] = useState(emptyOffer())
  const [image, setImage] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Магазин из адреса подставляем, как только список магазинов загрузился
  const preset = shops.data?.find((s) => s.name === params.get('shop'))
  const draft = offer.shopId === 0 && preset ? { ...offer, shopId: preset.id } : offer

  // Похожие чаи этого вида — чтобы не завести дубль
  const q = title.trim()
  const similar = useAsync(
    () => (category && q.length >= 3 ? api.getTeas({ category, q, sort: 'title' }) : Promise.resolve([])),
    [category, q],
  )
  const cat = categories.bySlug(category)
  const sortedShops = [...(shops.data ?? [])].sort((a, b) => a.title.localeCompare(b.title, 'ru'))

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!category) return setError('Выберите вид чая')
    if (!draft.shopId) return setError('Выберите магазин, где продаётся чай')
    setBusy(true)
    setError(null)
    try {
      const { shopId, ...rest } = offerInput(draft)
      const tea = await api.createTea({ category, title, region: region || null, description, shopId, offer: rest })
      // Фото не загрузилось — чай всё равно создан; загрузить можно на его странице
      if (image) await api.uploadTeaImage(tea.id, image).catch(() => undefined)
      navigate(fromDiary ? `/diary?add=${tea.id}` : `/teas/${tea.id}`)
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <div className="page" style={{ gap: 32 }}>
      <PageHero
        color={cat?.color ?? 'var(--accent-soft)'}
        eyebrow="Каталог"
        title={cat ? `Новый чай: ${cat.name.toLowerCase()}` : 'Добавить чай'}
        lead={
          fromDiary
            ? 'Чая нет в каталоге — добавьте его, и вернёмся к записи в дневнике.'
            : 'Один чай может продаваться в нескольких магазинах. Если он уже есть в каталоге — просто добавьте свой магазин на его странице.'
        }
      />

      <form className="card stack add-tea" onSubmit={submit} style={{ gap: 20 }}>
        <div className="field">
          Вид чая
          <div className="row chip-row" style={{ gap: 8 }} role="group" aria-label="Вид чая">
            {categories.list.map((c) => (
              <button key={c.slug} type="button" className="chip" aria-pressed={category === c.slug} onClick={() => setCategory(c.slug)}>
                <span className="dot" style={{ background: c.ink }} aria-hidden="true" />
                {c.name}
              </button>
            ))}
          </div>
        </div>

        <label className="field">
          Название
          <input className="input" required maxLength={128} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Габа Алишань" />
        </label>
        {similar.data && similar.data.length > 0 && (
          <div className="card stack" style={{ background: 'var(--butter)', gap: 6 }} role="status">
            <strong>Похоже, такой чай уже есть:</strong>
            {similar.data.slice(0, 5).map((t) => (
              <Link key={t.id} to={fromDiary ? `/diary?add=${t.id}` : `/teas/${t.id}`} style={{ fontWeight: 700 }}>
                {t.title} <span className="muted small">· {t.offers.map((o) => o.shop.title).join(', ')}</span>
              </Link>
            ))}
            <span className="small muted">
              {fromDiary
                ? 'Если это он — нажмите на него, и он выберется в записи дневника.'
                : 'Если это он — откройте его и добавьте свой магазин в блоке «Где купить».'}
            </span>
          </div>
        )}

        <label className="field">
          Регион <span className="muted" style={{ fontWeight: 500 }}>необязательно</span>
          <input className="input" maxLength={128} value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Тайвань, Алишань" />
        </label>
        <label className="field">
          Описание <span className="muted" style={{ fontWeight: 500 }}>необязательно</span>
          <textarea className="textarea" maxLength={4000} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Что это за чай, чем примечателен" />
        </label>

        <ImageField label="Фото чая" hint="Сухой лист, настой или упаковка. JPEG, PNG или WebP до 10 МБ." file={image} onChange={setImage} />

        <h3>Где продаётся</h3>
        <OfferFields
          value={draft}
          onChange={setOffer}
          shops={sortedShops}
          backTo={`/teas/new?${new URLSearchParams({ ...(category && { category }), ...(title && { title }), ...(fromDiary && { next: 'diary' }) })}`}
        />

        {error && <p className="error" role="alert">{error}</p>}
        <div className="row">
          <button className="btn" disabled={busy}>{busy ? 'Добавляем…' : 'Добавить чай'}</button>
          <Link to={fromDiary ? '/diary?add' : category ? `/teas?category=${category}` : '/teas'} className="btn btn-ghost">Отмена</Link>
        </div>
      </form>
    </div>
  )
}
