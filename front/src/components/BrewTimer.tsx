import { useEffect, useRef, useState } from 'react'

/** Время первого пролива и прибавка к каждому следующему, сек — по виду чая. */
const PRESETS: Record<string, [number, number]> = {
  green: [30, 10],
  white: [20, 10],
  yellow: [25, 10],
  oolong: [15, 5],
  gaba: [15, 5],
  red: [15, 5],
  shu: [10, 5],
  sheng: [10, 5],
  heicha: [10, 5],
  herbal: [120, 30],
}

/** Короткий сигнал, когда пролив готов (без файлов — генерируем звук). */
function beep() {
  try {
    const ctx = new AudioContext()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.frequency.value = 880
    gain.gain.setValueAtTime(0.2, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6)
    osc.connect(gain).connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.6)
    navigator.vibrate?.(200)
  } catch {
    /* звук не обязателен */
  }
}

/** Таймер проливов: считает время каждого пролива, по завершении — число проливов в запись. */
export function BrewTimer({ category, onDone }: { category?: string; onDone: (infusions: number) => void }) {
  const [open, setOpen] = useState(false)
  const preset = PRESETS[category ?? ''] ?? [15, 5]
  // null — не трогали: берём значение по виду чая (и оно меняется вместе с выбранным чаем)
  const [firstSet, setFirst] = useState<number | null>(null)
  const [stepSet, setStep] = useState<number | null>(null)
  const first = firstSet ?? preset[0]
  const step = stepSet ?? preset[1]
  const [n, setN] = useState(1) // номер текущего пролива
  const [left, setLeft] = useState<number | null>(null) // секунд до конца; null — не идёт
  const [done, setDone] = useState(0) // сколько проливов уже слито
  const timer = useRef<number | null>(null)

  useEffect(() => () => {
    if (timer.current) clearInterval(timer.current)
  }, [])

  const duration = first + step * (n - 1)

  function start() {
    if (timer.current) clearInterval(timer.current)
    const end = Date.now() + duration * 1000
    setLeft(duration)
    timer.current = window.setInterval(() => {
      const s = Math.max(0, Math.ceil((end - Date.now()) / 1000))
      setLeft(s)
      if (s === 0) {
        clearInterval(timer.current!)
        timer.current = null
        beep()
        setDone((d) => d + 1)
        setN((x) => x + 1)
        setLeft(null)
      }
    }, 200)
  }

  function stop() {
    if (timer.current) clearInterval(timer.current)
    timer.current = null
    setLeft(null)
  }

  function reset() {
    stop()
    setN(1)
    setDone(0)
  }

  if (!open) {
    return (
      <div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setOpen(true)}>⏱ Таймер проливов</button>
      </div>
    )
  }

  return (
    <div className="timer card" style={{ background: 'var(--bg)' }}>
      <div className="row" style={{ gap: 10 }}>
        <label className="field" style={{ flex: '1 1 120px' }}>
          Первый пролив, сек
          <input className="input" type="number" min={1} max={600} value={first} onChange={(e) => setFirst(Number(e.target.value))} />
        </label>
        <label className="field" style={{ flex: '1 1 120px' }}>
          Прибавлять, сек
          <input className="input" type="number" min={0} max={300} value={step} onChange={(e) => setStep(Number(e.target.value))} />
        </label>
      </div>
      <div className="timer-face" aria-live="polite">
        <span className="small muted">Пролив {n} · {duration} сек</span>
        <span className="timer-time">{left ?? duration}</span>
        <span className="small muted">Слито проливов: {done}</span>
      </div>
      <div className="row" style={{ gap: 8, justifyContent: 'center' }}>
        {left === null ? (
          <button type="button" className="btn" onClick={start}>Залить · {n}-й пролив</button>
        ) : (
          <button type="button" className="btn" onClick={stop}>Стоп</button>
        )}
        {done > 0 && left === null && (
          <button type="button" className="btn btn-ghost" onClick={() => onDone(done)}>
            Записать {done} в «Проливы»
          </button>
        )}
        <button type="button" className="btn btn-ghost btn-sm" onClick={reset}>Сначала</button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => { stop(); setOpen(false) }}>Свернуть</button>
      </div>
    </div>
  )
}
