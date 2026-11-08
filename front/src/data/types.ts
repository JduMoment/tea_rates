/** Типы ответов API (FastAPI, поля в camelCase). */

export interface Category {
  id: number
  /** Для адресов и фильтров: gaba */
  slug: string
  name: string // «Габа»
  plural: string // «Габы»
  instrumental: string // «габами» — для фраз «славится габами»
  color: string // фон плашки
  ink: string // цвет иконки/акцента
}

export interface ShopBrief {
  id: number
  /** Для адресов и фильтров: art-of-tea */
  name: string
  title: string
}

export interface Shop extends ShopBrief {
  country: string
  city: string
  site: string
  founded: number | null
  description: string
}

export interface Stats {
  avg: number
  reviews: number
}

/** Чай в конкретном магазине. */
export interface Offer {
  id: number
  teaId: number
  shopId: number
  shop: ShopBrief
  /** Текущая цена за weight граммов: из последнего отзыва с ценой, иначе указанная при добавлении. */
  price: number | null
  weight: number | null
  priceLabel: string | null // «1 450 ₽ / 50 г»
  /** Когда цена была актуальна (ISO): дата отзыва или добавления магазина. */
  priceDate: string | null
  /** review — из отзыва, offer — указана при добавлении магазина. */
  priceSource: 'review' | 'offer' | null
  url: string | null
  authorId: number | null
}

/** Предложение с оценкой чая именно из этого магазина. */
export interface RatedOffer extends Offer {
  stats: Stats
  /** Место магазина в рейтинге по виду этого чая. */
  shopRank: number | null
}

export type Season = 'spring' | 'summer' | 'autumn' | 'winter'

export const SEASONS: { id: Season; label: string }[] = [
  { id: 'spring', label: 'Весна' },
  { id: 'summer', label: 'Лето' },
  { id: 'autumn', label: 'Осень' },
  { id: 'winter', label: 'Зима' },
]

export interface Tea {
  id: number
  name: string
  categoryId: number
  title: string
  region: string | null
  description: string
  authorId: number | null
  category: Category
  /** Где продаётся, дешёвые первыми. */
  offers: Offer[]
  stats: Stats
  /** Только при поиске по вкусу: совпадение с выбранными нотами; null — о вкусе ещё не писали. */
  flavorMatch?: FlavorMatch | null
}

export interface FlavorMatch {
  /** slug'и выбранных нот, которые слышат в чае, — частые первыми */
  flavors: string[]
  /** Доля отзывов с нотами, где есть хоть одна из выбранных, 0–1 */
  share: number
}

/** «Вам может понравиться» */
export interface Recommendations {
  /** Отзывов пользователя с нотами */
  reviews: number
  /** Сколько нужно, чтобы появились советы */
  needed: number
  items: { tea: Tea; reasons: string[]; score: number }[]
}

export interface User {
  id: number
  name: string
  email: string
  joined: string // ISO
}

export interface Review {
  id: number
  teaId: number
  shopId: number
  userId: number
  rating: number // 1–5
  text: string
  /** slug'и дескрипторов колеса */
  flavors: string[]
  createdAt: string // ISO
  /** Покупка: цена за weight граммов и партия. Всё необязательно. */
  price: number | null
  weight: number | null
  priceLabel: string | null // «1 450 ₽ / 50 г»
  harvestYear: number | null
  harvestSeason: Season | null
  harvest: string // «Весна 2025» или ''
  /** Настой по шкалам 1–5 (null — не оценивал): тело, насыщенность, послевкусие */
  body: number | null
  strength: number | null
  aftertaste: number | null
  /** Сколько отметили полезным; voted — отметил ли я */
  helpful: number
  voted: boolean
  photos: Photo[]
  user: Pick<User, 'id' | 'name'>
  shop: ShopBrief
  /** Есть в лентах, на странице чая — нет. */
  tea?: Tea | null
}

export interface Photo {
  id: number
  url: string
  thumbUrl: string
  width: number
  height: number
}

/** Средние шкалы настоя по отзывам; null — никто не отметил */
export interface InfusionStats {
  body: number | null
  strength: number | null
  aftertaste: number | null
  reviews: number
}

/** Медианы по дневникам */
export interface Brewed {
  entries: number
  people: number
  water: number
  grams: number
  infusions: number
  volume: number | null
  gramsPer100: number | null
}

/** Как заваривают чай: community/liked — null, пока записей мало */
export interface Brewing {
  category: string
  typical: { water: [number, number]; gramsPer100: [number, number]; infusions: [number, number] }
  community: Brewed | null
  liked: Brewed | null
}

export interface ShopPrices {
  shop: ShopBrief
  points: { at: string; price: number; weight: number; perGram: number; source: 'review' | 'offer' }[]
}

/** Публичный профиль автора */
export interface Author {
  id: number
  name: string
  joined: string
  reviews: number
  teas: number
  followers: number
  following: number
  followedByMe: boolean
}

export type ShelfStatus = 'want' | 'have' | 'finished'

export const SHELF_STATUSES: { id: ShelfStatus; label: string }[] = [
  { id: 'want', label: 'Хочу попробовать' },
  { id: 'have', label: 'Есть дома' },
  { id: 'finished', label: 'Закончился' },
]

export interface ShelfItem {
  status: ShelfStatus
  statusLabel: string
  updatedAt: string
  tea: Tea
}

// ---------- колесо вкусов ----------

export interface TasteInfo {
  slug: string
  title: string
  color: string
}

export interface FlavorInfo {
  slug: string
  title: string
  /** slug вкуса */
  taste: string
}

export interface FlavorGroupInfo {
  slug: string
  title: string
  color: string
  flavors: FlavorInfo[]
}

export interface FlavorWheel {
  tastes: TasteInfo[]
  /** По часовой стрелке от «12 часов». */
  groups: FlavorGroupInfo[]
}

export interface Share {
  slug: string
  count: number
  /** Доля отзывов (с дескрипторами), 0–1 */
  share: number
}

export interface FlavorProfile {
  reviews: number
  flavors: Share[]
  groups: Share[]
  tastes: Share[]
}

export interface TeaDetails extends Omit<Tea, 'offers'> {
  offers: RatedOffer[]
  reviews: Review[]
  /** Другие чаи этого вида. */
  alternatives: Tea[]
  flavorProfile: FlavorProfile
  infusion: InfusionStats
}

// ---------- магазины и рейтинги ----------

/** Средняя оценка магазина в одном виде чая. */
export interface ShopCategoryScore {
  shopId: number
  categoryId: number
  avg: number
  reviews: number
  teas: number
}

export interface ShopSummary extends Shop {
  stats: Stats
  teaCount: number
  specialties: ShopCategoryScore[]
}

export interface ShopDetails extends ShopSummary {
  scores: ShopCategoryScore[]
  teas: Tea[]
}

export interface CategoryRankingRow {
  shop: Shop
  score: ShopCategoryScore
  bestTea: Tea
  bestOffer: RatedOffer
}

export interface CategoryLeader {
  category: Category
  leader: CategoryRankingRow
}

export interface ShopRankingRow {
  shop: ShopSummary
  /** id видов чая, где магазин на первом месте */
  leads: number[]
  scores: ShopCategoryScore[]
}

// ---------- дневник ----------

export interface DiaryEntry {
  id: number
  userId: number
  teaId: number
  shopId: number
  date: string // YYYY-MM-DD
  rating: number
  water: number // °C
  grams: number
  /** Объём посуды, мл */
  volume: number | null
  infusions: number
  text: string
  tea: Tea
  shop: ShopBrief
}
