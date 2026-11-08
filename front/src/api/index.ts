/** Клиент API. Каждая функция — один эндпоинт FastAPI (путь в комментарии). */
import type {
  Author,
  Brewing,
  Category,
  CategoryLeader,
  CategoryRankingRow,
  DiaryEntry,
  FlavorProfile,
  FlavorWheel,
  Recommendations,
  Review,
  Season,
  ShelfItem,
  ShelfStatus,
  ShopDetails,
  ShopPrices,
  ShopRankingRow,
  ShopSummary,
  Tea,
  TeaDetails,
} from '../data/types'
import { ApiError } from './errors'
import { http } from './http'

export { ApiError }

export type TeaSort = 'rating' | 'reviews' | 'price' | 'title'

function query(params: Record<string, string | number | string[] | undefined | null>) {
  const q = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) value.forEach((v) => q.append(key, v))
    else if (value !== undefined && value !== null && value !== '') q.set(key, String(value))
  }
  const s = q.toString()
  return s ? `?${s}` : ''
}

/** Справочники не меняются без деплоя — грузим один раз за жизнь страницы. */
function once<T>(load: () => Promise<T>) {
  let cached: Promise<T> | null = null
  return () => {
    cached ??= load().catch((e: unknown) => {
      cached = null // ошибку не кешируем — следующий вызов попробует снова
      throw e
    })
    return cached
  }
}

// ---------- справочники ----------

/** GET /api/categories */
export const getCategories = once(() => http<Category[]>('/categories'))

/** GET /api/flavors — колесо вкусов */
export const getFlavorWheel = once(() => http<FlavorWheel>('/flavors'))

// ---------- магазины ----------

/** GET /api/shops */
export const getShops = () => http<ShopSummary[]>('/shops')

/** GET /api/shops/{name} */
export const getShop = (name: string) => http<ShopDetails>(`/shops/${encodeURIComponent(name)}`)

// ---------- рейтинги ----------

/** GET /api/rankings/categories/{slug} — магазины по оценке их чаёв этого вида */
export const getCategoryRanking = (slug: string) =>
  http<CategoryRankingRow[]>(`/rankings/categories/${encodeURIComponent(slug)}`)

/** GET /api/rankings/leaders — лидер каждого вида (для главной) */
export const getCategoryLeaders = () => http<CategoryLeader[]>('/rankings/leaders')

/** GET /api/rankings/shops */
export const getShopRanking = () => http<ShopRankingRow[]>('/rankings/shops')

/** GET /api/rankings/teas?category=gaba&category=red&limit= */
export const getTopTeas = (params: { categories?: string[]; limit?: number } = {}) =>
  http<Tea[]>(`/rankings/teas${query({ category: params.categories, limit: params.limit })}`)

// ---------- чаи ----------

/** GET /api/teas?category=&shop=&q=&flavor=&flavor=&sort= — с flavor это поиск по вкусу (у чаёв есть flavorMatch) */
export const getTeas = (
  params: { category?: string; shop?: string; q?: string; flavors?: string[]; sort?: TeaSort } = {},
) => {
  const { flavors, ...rest } = params
  return http<Tea[]>(`/teas${query({ ...rest, flavor: flavors })}`)
}

/** GET /api/teas/{id} */
export const getTea = (id: number | string) => http<TeaDetails>(`/teas/${id}`)

/** GET /api/users/{id}/flavors — что пользователь отмечал в своих отзывах */
export const getUserFlavors = (userId: number) => http<FlavorProfile>(`/users/${userId}/flavors`)

/** GET /api/me/recommendations?limit= — «Вам может понравиться» */
export const getRecommendations = (limit = 12) => http<Recommendations>(`/me/recommendations${query({ limit })}`)

/** GET /api/teas/{id}/flavors?shop= — вкусовой профиль по отзывам одного магазина */
export const getTeaFlavors = (id: number, shop?: string) => http<FlavorProfile>(`/teas/${id}/flavors${query({ shop })}`)

/** Магазин продаёт чай. Цена — текущая на сайте, необязательна (дальше её обновляют отзывы). */
export interface OfferInput {
  price?: number | null
  weight?: number | null
  url?: string | null
}

/** Отзыв на покупку. Цена (вместе с весом) и партия — необязательные сведения о ней. */
export interface ReviewInput {
  shopId: number
  rating: number
  text: string
  flavors: string[]
  price?: number | null
  weight?: number | null
  harvestYear?: number | null
  harvestSeason?: Season | null
  /** Настой 1–5, необязательно */
  body?: number | null
  strength?: number | null
  aftertaste?: number | null
}

/** POST /api/teas — новый чай сразу с первым магазином */
export const createTea = (data: {
  category: string
  title: string
  region?: string | null
  description?: string
  shopId: number
  offer: OfferInput
}) => http<TeaDetails>('/teas', { method: 'POST', body: data })

/** DELETE /api/teas/{id} — только автор и пока нет чужих отзывов */
export const deleteTea = (id: number) => http<void>(`/teas/${id}`, { method: 'DELETE' })

/** POST /api/teas/{id}/offers — этот чай есть ещё и в магазине shopId */
export const addOffer = (teaId: number, data: OfferInput & { shopId: number }) =>
  http<TeaDetails>(`/teas/${teaId}/offers`, { method: 'POST', body: data })

/** DELETE /api/teas/{id}/offers/{shopId} */
export const deleteOffer = (teaId: number, shopId: number) =>
  http<void>(`/teas/${teaId}/offers/${shopId}`, { method: 'DELETE' })

// ---------- отзывы ----------

/** GET /api/reviews?limit= */
export const getRecentReviews = (limit = 6) => http<Review[]>(`/reviews${query({ limit })}`)

/** GET /api/users/{id}/reviews */
export const getUserReviews = (userId: number) => http<Review[]>(`/users/${userId}/reviews`)

/** POST /api/teas/{teaId}/reviews — повторный отзыв на тот же чай из того же магазина заменяет прежний */
export const addReview = (teaId: number, data: ReviewInput) => http<Review>(`/teas/${teaId}/reviews`, { method: 'POST', body: data })

/** DELETE /api/reviews/{id} */
export const deleteReview = (reviewId: number) => http<void>(`/reviews/${reviewId}`, { method: 'DELETE' })

// ---------- дневник ----------

/** GET /api/diary */
export const getDiary = () => http<DiaryEntry[]>('/diary')

/** POST /api/diary */
export const addDiaryEntry = (data: {
  teaId: number
  shopId: number
  date: string
  rating: number
  water: number
  grams: number
  volume: number | null
  infusions: number
  text: string
}) => http<DiaryEntry>('/diary', { method: 'POST', body: data })

/** DELETE /api/diary/{id} */
export const deleteDiaryEntry = (id: number) => http<void>(`/diary/${id}`, { method: 'DELETE' })

/** PUT /api/reviews/{id}/vote — «полезный отзыв» */
export const voteReview = (reviewId: number, helpful: boolean) =>
  http<Review>(`/reviews/${reviewId}/vote`, { method: 'PUT', body: { helpful } })

/** POST /api/reviews/{id}/photos — multipart, поле file */
export async function uploadReviewPhoto(reviewId: number, file: File): Promise<Review> {
  const form = new FormData()
  form.append('file', file)
  let res: Response
  try {
    res = await fetch(`/api/reviews/${reviewId}/photos`, { method: 'POST', body: form, credentials: 'same-origin' })
  } catch {
    throw new ApiError('Нет связи с сервером', 0)
  }
  const body = (await res.json().catch(() => null)) as { detail?: unknown } | null
  if (!res.ok) throw new ApiError(typeof body?.detail === 'string' ? body.detail : `Не удалось загрузить фото (${res.status})`, res.status)
  return body as unknown as Review
}

/** DELETE /api/reviews/{id}/photos/{photoId} */
export const deleteReviewPhoto = (reviewId: number, photoId: number) =>
  http<void>(`/reviews/${reviewId}/photos/${photoId}`, { method: 'DELETE' })

// ---------- заваривание и цены ----------

/** GET /api/teas/{id}/brewing — как заваривают */
export const getBrewing = (teaId: number) => http<Brewing>(`/teas/${teaId}/brewing`)

/** GET /api/teas/{id}/prices — история цены по магазинам */
export const getPrices = (teaId: number) => http<ShopPrices[]>(`/teas/${teaId}/prices`)

// ---------- шкаф ----------

/** GET /api/me/shelf */
export const getShelf = () => http<ShelfItem[]>('/me/shelf')

/** PUT /api/me/shelf/{teaId} */
export const putShelf = (teaId: number, status: ShelfStatus) =>
  http<ShelfItem>(`/me/shelf/${teaId}`, { method: 'PUT', body: { status } })

/** DELETE /api/me/shelf/{teaId} */
export const removeFromShelf = (teaId: number) => http<void>(`/me/shelf/${teaId}`, { method: 'DELETE' })

// ---------- авторы и подписки ----------

/** GET /api/users/{id} */
export const getAuthor = (userId: number | string) => http<Author>(`/users/${userId}`)

/** PUT /api/users/{id}/follow */
export const followAuthor = (userId: number, follow: boolean) =>
  http<Author>(`/users/${userId}/follow`, { method: 'PUT', body: { follow } })

/** GET /api/me/following */
export const getFollowing = () => http<{ id: number; name: string }[]>('/me/following')

/** GET /api/me/feed — свежие отзывы тех, на кого подписан */
export const getFeed = (limit = 12) => http<Review[]>(`/me/feed${query({ limit })}`)
