type P = { size?: number; color?: string }

export const LeafIcon = ({ size = 20, color = 'currentColor' }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" aria-hidden="true">
    <path d="M5 19C5 10 11 4 20 4c0 9-6 15-15 15z" />
    <path d="M5 19L14 10" />
  </svg>
)

export const CupIcon = ({ size = 96, color = 'currentColor' }: P) => (
  <svg width={size} height={size} viewBox="0 0 96 96" fill="none" stroke={color} strokeWidth="2" aria-hidden="true">
    <path d="M18 44h52v8c0 14-11 26-26 26S18 66 18 52v-8z" />
    <path d="M70 50h6a8 8 0 0 1 0 16h-8" />
    <path d="M36 22c0 5 4 5 4 10M48 18c0 5 4 5 4 10" />
  </svg>
)

export const SearchIcon = ({ size = 18, color = 'currentColor' }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" aria-hidden="true">
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" />
  </svg>
)

export const StoreIcon = ({ size = 18, color = 'currentColor' }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" aria-hidden="true">
    <path d="M4 10v10h16V10" />
    <path d="M2 10l2-6h16l2 6c0 1.7-1.3 3-3 3s-3-1.3-3-3c0 1.7-1.3 3-3 3s-3-1.3-3-3c0 1.7-1.3 3-3 3s-3-1.3-3-3z" />
  </svg>
)

/** Знак Яндекса для кнопки «Войти с Яндекс ID» */
export const YandexIcon = ({ size = 22 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="12" fill="#FC3F1D" />
    <path d="M13.3 6h-1.2C9.9 6 8.7 7.2 8.7 8.9c0 1.4.7 2.3 2 3.2L8.4 18h1.8l2.5-5.5h.6V18h1.6V6h-1.6zm0 5.2h-.6c-1.2 0-2.2-.6-2.2-2.3 0-1.6.9-2.3 2-2.3h.8v4.6z" fill="#fff" />
  </svg>
)
