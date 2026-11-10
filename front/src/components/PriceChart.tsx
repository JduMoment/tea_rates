import { useEffect, useMemo, useRef, useState, type PointerEvent } from 'react'
import type { ShopPrices } from '../data/types'
import { fmtPerGram } from '../utils/format'

/** Категориальная палитра в фиксированном порядке (проверена на различимость, в т.ч. при дальтонизме).
 *  Цвет закреплён за магазином по его порядку в «Где купить», а не по месту на графике. */
const SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']

const M = { top: 16, right: 16, bottom: 30, left: 56 }
const month = (t: number) => new Date(t).toLocaleDateString('ru-RU', { month: 'short', year: 'numeric' })

/** Красивые деления оси Y: 3–5 штук, шаг 1/2/5 × 10ⁿ. */
function ticks(min: number, max: number) {
  const span = max - min || max || 1
  const raw = span / 4
  const pow = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((k) => k * pow).find((s) => s >= raw)!
  const lo = Math.floor(min / step) * step
  const hi = Math.ceil(max / step) * step
  const out: number[] = []
  for (let v = lo; v <= hi + step / 2; v += step) out.push(Number(v.toFixed(6)))
  return out
}

/** История цены за грамм по магазинам: линия на магазин, наведение — вертикаль и значения всех магазинов. */
export function PriceChart({ data }: { data: ShopPrices[] }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const [hoverT, setHoverT] = useState<number | null>(null)
  // Рисуем в настоящих пикселях контейнера: так подписи осей всегда 12px, и на телефоне тоже
  const [W, setW] = useState(720)
  const H = W < 480 ? 220 : 260
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const geo = useMemo(() => {
    const series = data.map((s, i) => ({
      ...s,
      color: SERIES[i % SERIES.length],
      pts: s.points.map((p) => ({ ...p, t: new Date(p.at).getTime() })),
    }))
    const all = series.flatMap((s) => s.pts)
    const t0 = Math.min(...all.map((p) => p.t))
    const t1 = Math.max(...all.map((p) => p.t))
    const yTicks = ticks(Math.min(...all.map((p) => p.perGram)) * 0.95, Math.max(...all.map((p) => p.perGram)) * 1.05)
    const y0 = yTicks[0]
    const y1 = yTicks[yTicks.length - 1]
    const x = (t: number) => M.left + (t1 === t0 ? 0.5 : (t - t0) / (t1 - t0)) * (W - M.left - M.right)
    const y = (v: number) => H - M.bottom - ((v - y0) / (y1 - y0 || 1)) * (H - M.top - M.bottom)
    // 3–4 подписи по оси X: начало, конец и между ними
    // На узком экране — две подписи по краям, иначе 3–4
    const steps = W < 480 ? [0, 1] : [0, 1 / 3, 2 / 3, 1]
    const xTicks = t1 === t0 ? [t0] : steps.map((k) => t0 + k * (t1 - t0))
    return { series, x, y, yTicks, xTicks, t0, t1 }
  }, [data, W, H])

  function onMove(e: PointerEvent<SVGSVGElement>) {
    const box = svgRef.current!.getBoundingClientRect()
    const px = ((e.clientX - box.left) / box.width) * W
    // Ближайшая по времени точка любого магазина — к ней «прилипает» вертикаль
    let best: number | null = null
    for (const s of geo.series)
      for (const p of s.pts) if (best === null || Math.abs(geo.x(p.t) - px) < Math.abs(geo.x(best) - px)) best = p.t
    setHoverT(best)
  }

  // На наведённую дату у каждого магазина — его последняя известная цена к этому моменту
  const hover =
    hoverT === null
      ? []
      : geo.series
          .map((s) => ({ s, p: [...s.pts].reverse().find((p) => p.t <= hoverT) }))
          .filter((x): x is { s: (typeof geo.series)[number]; p: (typeof geo.series)[number]['pts'][number] } => Boolean(x.p))
  const tipLeft = hoverT === null ? 0 : (geo.x(hoverT) / W) * 100

  return (
    <div className="stack" style={{ gap: 10 }}>
      {geo.series.length > 1 && (
        <div className="row chart-legend" style={{ gap: 16 }}>
          {geo.series.map((s) => (
            <span key={s.shop.id} className="row small" style={{ gap: 6 }}>
              <span className="legend-key" style={{ background: s.color }} aria-hidden="true" />
              {s.shop.title}
            </span>
          ))}
        </div>
      )}
      <div className="chart-wrap" ref={wrapRef}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          height={H}
          className="price-chart"
          role="img"
          aria-label="История цены за грамм по магазинам"
          onPointerMove={onMove}
          onPointerLeave={() => setHoverT(null)}
        >
          {geo.yTicks.map((v) => (
            <g key={v}>
              <line x1={M.left} x2={W - M.right} y1={geo.y(v)} y2={geo.y(v)} className="chart-grid" />
              <text x={M.left - 8} y={geo.y(v)} className="chart-axis" textAnchor="end" dominantBaseline="central">
                {fmtPerGram(v)}
              </text>
            </g>
          ))}
          {geo.xTicks.map((t, i) => (
            <text key={t} x={geo.x(t)} y={H - 8} className="chart-axis" textAnchor={i === 0 ? 'start' : i === geo.xTicks.length - 1 ? 'end' : 'middle'}>
              {month(t)}
            </text>
          ))}
          {hoverT !== null && <line x1={geo.x(hoverT)} x2={geo.x(hoverT)} y1={M.top} y2={H - M.bottom} className="chart-cross" />}
          {geo.series.map((s) => (
            <g key={s.shop.id}>
              <polyline
                points={s.pts.map((p) => `${geo.x(p.t)},${geo.y(p.perGram)}`).join(' ')}
                fill="none"
                stroke={s.color}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {s.pts.map((p) => (
                <circle key={p.t} cx={geo.x(p.t)} cy={geo.y(p.perGram)} r={4} fill={s.color} stroke="#fff" strokeWidth={2} />
              ))}
            </g>
          ))}
        </svg>
        {hover.length > 0 && (
          <div className="chart-tip" style={{ left: `${tipLeft}%`, transform: `translateX(${tipLeft > 50 ? '-104%' : '4%'})` }} role="status">
            <strong className="small">{new Date(hoverT!).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}</strong>
            {hover.map(({ s, p }) => (
              <span key={s.shop.id} className="row small" style={{ gap: 6 }}>
                <span className="legend-key" style={{ background: s.color }} aria-hidden="true" />
                {s.shop.title}: <strong>{fmtPerGram(p.perGram)}</strong>
                <span className="muted">({p.price.toLocaleString('ru-RU')} ₽ / {p.weight} г)</span>
              </span>
            ))}
          </div>
        )}
      </div>
      <details className="small">
        <summary>Показать таблицей</summary>
        <div className="table-scroll">
        <table className="chart-table">
          <thead>
            <tr><th>Дата</th><th>Магазин</th><th>Цена</th><th>За грамм</th><th>Откуда</th></tr>
          </thead>
          <tbody>
            {geo.series
              .flatMap((s) => s.pts.map((p) => ({ s, p })))
              .sort((a, b) => b.p.t - a.p.t)
              .map(({ s, p }) => (
                <tr key={`${s.shop.id}-${p.t}`}>
                  <td>{new Date(p.t).toLocaleDateString('ru-RU')}</td>
                  <td>{s.shop.title}</td>
                  <td>{p.price.toLocaleString('ru-RU')} ₽ / {p.weight} г</td>
                  <td>{fmtPerGram(p.perGram)}</td>
                  <td>{p.source === 'review' ? 'из отзыва' : 'цена на сайте'}</td>
                </tr>
              ))}
          </tbody>
        </table>
        </div>
      </details>
    </div>
  )
}
