import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useLocation } from 'react-router'
import { ApiError, sendFeedback } from '../api'
import { useAuth } from '../auth/AuthContext'

const MAX = 2000

/** Кнопка «Нашли ошибку?» в шапке и окно обратной связи. Писать может и гость. */
export function FeedbackButton({ className }: { className?: string }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" className={className} onClick={() => setOpen(true)}>
        Нашли ошибку?
      </button>
      {open && <FeedbackDialog onClose={() => setOpen(false)} />}
    </>
  )
}

function FeedbackDialog({ onClose }: { onClose: () => void }) {
  const { user } = useAuth()
  const { pathname, search } = useLocation()
  const ref = useRef<HTMLDialogElement>(null)
  const [text, setText] = useState('')
  const [email, setEmail] = useState('')
  const [website, setWebsite] = useState('') // ловушка для ботов
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)

  useEffect(() => {
    const dialog = ref.current
    dialog?.showModal()
    return () => dialog?.close()
  }, [])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await sendFeedback({ text, email: user ? null : email || null, page: pathname + search, website })
      setSent(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не получилось отправить')
    } finally {
      setBusy(false)
    }
  }

  return (
    <dialog
      ref={ref}
      className="feedback-dialog"
      aria-labelledby="feedback-title"
      onClose={onClose}
      // клик по затемнению вокруг окна закрывает его
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      {sent ? (
        <div className="stack">
          <h2 id="feedback-title">Спасибо!</h2>
          <p>Сообщение отправлено — разберёмся.{user || email ? ' Если понадобятся подробности, ответим на почту.' : ''}</p>
          <div className="row">
            <button type="button" className="btn" autoFocus onClick={onClose}>Закрыть</button>
          </div>
        </div>
      ) : (
        <form className="stack" onSubmit={submit}>
          <h2 id="feedback-title">Обратная связь</h2>
          <p className="muted" style={{ margin: 0 }}>
            Напишите, что сломалось, что неудобно или поделитесь идеей.
          </p>
          <label className="field">
            Сообщение
            <textarea
              className="textarea"
              required
              autoFocus
              maxLength={MAX}
              placeholder="Что делали, что ожидали увидеть и что произошло"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            {text.length > MAX - 200 && <span className="small muted">{text.length} / {MAX}</span>}
          </label>
          {user ? (
            <p className="small muted" style={{ margin: 0 }}>Ответим на {user.email}, если понадобится.</p>
          ) : (
            <label className="field">
              <span>
                Почта для ответа <span className="muted" style={{ fontWeight: 500 }}>(необязательно)</span>
              </span>
              <input className="input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
          )}
          <input
            className="feedback-trap"
            tabIndex={-1}
            autoComplete="off"
            aria-hidden="true"
            name="website"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
          />
          {error && <p className="error" role="alert" style={{ margin: 0 }}>{error}</p>}
          <div className="row" style={{ gap: 8 }}>
            <button type="submit" className="btn" disabled={busy || !text.trim()}>
              {busy ? 'Отправляем…' : 'Отправить'}
            </button>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Отмена</button>
          </div>
        </form>
      )}
    </dialog>
  )
}
