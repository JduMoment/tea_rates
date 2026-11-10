import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router'
import { forgotPassword, OAUTH_ERRORS, yandexLoginUrl } from '../api/auth'
import { useAuth } from '../auth/AuthContext'
import { LeafIcon, YandexIcon } from '../components/Icons'
import { Loading } from '../components/Layout'

function useRedirectTarget() {
  const location = useLocation()
  return (location.state as { from?: string } | null)?.from ?? '/'
}

const PERKS = ['Оценивайте чаи у конкретных магазинов', 'Ведите личный чайный дневник', 'Смотрите, у кого какой чай лучше']

/** Общая раскладка: слева цветная плашка с заголовком и плюсами аккаунта, справа форма. */
function AuthLayout({ title, lead, color, children }: { title: ReactNode; lead: string; color: string; children: ReactNode }) {
  return (
    <div className="page">
      <div className="auth-layout">
        <section className="hero hero-page" style={{ background: color }}>
          <h1>{title}</h1>
          <p>{lead}</p>
          <ul className="perks">
            {PERKS.map((p) => (
              <li key={p}>
                <span className="cat-dot" style={{ width: 32, height: 32, background: 'var(--accent)' }}><LeafIcon size={16} /></span>
                {p}
              </li>
            ))}
          </ul>
        </section>
        {children}
      </div>
    </div>
  )
}

/** Кнопка Яндекс ID и разделитель перед формой с почтой. */
function OAuthButtons({ next }: { next: string }) {
  return (
    <>
      <a className="btn btn-ghost btn-yandex" href={yandexLoginUrl(next)}>
        <YandexIcon /> Войти с Яндекс ID
      </a>
      <p className="auth-divider small muted">или по почте</p>
    </>
  )
}

/** Текст ошибки из ?oauth_error= (бэкенд вернул сюда после неудачного входа через Яндекс); параметр убираем из адреса. */
function useOAuthError(): string | null {
  const [params, setParams] = useSearchParams()
  const code = params.get('oauth_error')
  const [message] = useState(() => (code ? OAUTH_ERRORS[code] ?? OAUTH_ERRORS.provider : null))
  useEffect(() => {
    if (code) setParams((p) => { p.delete('oauth_error'); return p }, { replace: true })
  }, [code, setParams])
  return message
}

function FormError({ error }: { error: string | null }) {
  return error ? <p className="error" role="alert">{error}</p> : null
}

export function Login() {
  const { user, ready, login } = useAuth()
  const navigate = useNavigate()
  const target = useRedirectTarget()
  const oauthError = useOAuthError()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(oauthError)
  const [busy, setBusy] = useState(false)

  if (!ready) return <Loading />
  if (user) return <Navigate to={target} replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email, password)
      navigate(target, { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title={<>С возвращением<br />к чаю</>} lead="Войдите, чтобы оставлять отзывы и вести дневник." color="var(--accent-soft)">
      <form className="auth-form" onSubmit={submit} noValidate>
        <h2>Вход</h2>
        <OAuthButtons next={target} />
        <label className="field">
          Почта
          <input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          <span className="row between">
            Пароль
            <Link to="/forgot-password" state={{ email }} className="small" style={{ fontWeight: 600 }}>Забыли пароль?</Link>
          </span>
          <input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <FormError error={error} />
        <button className="btn" disabled={busy || !email || !password}>{busy ? 'Входим…' : 'Войти'}</button>
        <p className="small muted">
          Нет аккаунта? <Link to="/register" state={{ from: target }} style={{ fontWeight: 700 }}>Зарегистрироваться</Link>
        </p>
      </form>
    </AuthLayout>
  )
}

export function Register() {
  const { user, ready, register } = useAuth()
  const navigate = useNavigate()
  const target = useRedirectTarget()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!ready) return <Loading />
  if (user) return <Navigate to={target} replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (password !== password2) return setError('Пароли не совпадают')
    setBusy(true)
    setError(null)
    try {
      await register(name, email, password)
      navigate(target === '/' ? '/diary' : target, { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title={<>Заведите свой<br />чайный дневник</>} lead="Регистрация занимает полминуты." color="var(--lilac)">
      <form className="auth-form" onSubmit={submit} noValidate>
        <h2>Регистрация</h2>
        <OAuthButtons next={target === '/' ? '/diary' : target} />
        <label className="field">
          Имя или ник
          <input className="input" autoComplete="nickname" required maxLength={64} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="field">
          Почта
          <input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          Пароль <span className="muted" style={{ fontWeight: 500 }}>минимум 6 символов</span>
          <input className="input" type="password" autoComplete="new-password" required minLength={6} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <label className="field">
          Пароль ещё раз
          <input className="input" type="password" autoComplete="new-password" required value={password2} onChange={(e) => setPassword2(e.target.value)} />
        </label>
        <FormError error={error} />
        <button className="btn" disabled={busy || !name || !email || !password || !password2}>{busy ? 'Создаём…' : 'Создать аккаунт'}</button>
        <p className="small muted">
          Уже есть аккаунт? <Link to="/login" state={{ from: target }} style={{ fontWeight: 700 }}>Войти</Link>
        </p>
      </form>
    </AuthLayout>
  )
}

/** «Забыли пароль?» — письмо со ссылкой. Ответ одинаковый для любой почты: не подсказываем, кто зарегистрирован. */
export function ForgotPassword() {
  const location = useLocation()
  const [email, setEmail] = useState((location.state as { email?: string } | null)?.email ?? '')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await forgotPassword(email)
      setSent(true)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title={<>Вспомним<br />пароль</>} lead="Пришлём ссылку, по которой можно задать новый." color="var(--butter)">
      <form className="auth-form" onSubmit={submit} noValidate>
        <h2>Новый пароль</h2>
        {sent ? (
          <>
            <p role="status">
              Если аккаунт с почтой <strong>{email}</strong> есть, мы отправили на неё письмо со ссылкой. Она действует час.
            </p>
            <p className="small muted">Письма нет? Проверьте «Спам» или запросите ещё раз через пару минут.</p>
            <Link to="/login" className="btn">Ко входу</Link>
          </>
        ) : (
          <>
            <label className="field">
              Почта, с которой регистрировались
              <input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <FormError error={error} />
            <button className="btn" disabled={busy || !email}>{busy ? 'Отправляем…' : 'Прислать ссылку'}</button>
            <p className="small muted">
              Вспомнили? <Link to="/login" style={{ fontWeight: 700 }}>Войти</Link>
            </p>
          </>
        )}
      </form>
    </AuthLayout>
  )
}

/** Страница из письма: /reset-password?token=… */
export function ResetPassword() {
  const { resetPassword } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (password !== password2) return setError('Пароли не совпадают')
    setBusy(true)
    setError(null)
    try {
      await resetPassword(token, password)
      navigate('/profile', { replace: true })
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <AuthLayout title={<>Новый<br />пароль</>} lead="После смены пароля все остальные устройства выйдут из аккаунта." color="var(--butter)">
      <form className="auth-form" onSubmit={submit} noValidate>
        <h2>Задайте пароль</h2>
        {!token ? (
          <p>
            В ссылке нет кода. Откройте ссылку из письма целиком или <Link to="/forgot-password">запросите новую</Link>.
          </p>
        ) : (
          <>
            <label className="field">
              Новый пароль <span className="muted" style={{ fontWeight: 500 }}>минимум 6 символов</span>
              <input className="input" type="password" autoComplete="new-password" required minLength={6} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            <label className="field">
              Ещё раз
              <input className="input" type="password" autoComplete="new-password" required value={password2} onChange={(e) => setPassword2(e.target.value)} />
            </label>
            <FormError error={error} />
            {error && <Link to="/forgot-password" className="small">Запросить новую ссылку</Link>}
            <button className="btn" disabled={busy || !password || !password2}>{busy ? 'Сохраняем…' : 'Сохранить и войти'}</button>
          </>
        )}
      </form>
    </AuthLayout>
  )
}
