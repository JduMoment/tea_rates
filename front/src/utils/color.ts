/** Тёмный или светлый текст поверх цвета; opacity — прозрачность заливки на белом фоне. */
export function textOn(hex: string, opacity = 1) {
  const n = parseInt(hex.slice(1), 16)
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => 255 + (c - 255) * opacity)
  return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? '#22301a' : '#ffffff'
}
