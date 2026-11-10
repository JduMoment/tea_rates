import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../auth/AuthContext'
import { FeedbackButton } from './FeedbackDialog'
import { PageHero } from './PageHero'

const SECTION_TITLES: [string, string][] = [
  ['/teas', 'Чаи'],
  ['/shops', 'Магазины'],
  ['/rankings', 'Рейтинги'],
  ['/diary', 'Дневник'],
  ['/profile', 'Профиль'],
  ['/login', 'Вход'],
  ['/register', 'Регистрация'],
  ['/forgot-password', 'Восстановление пароля'],
  ['/reset-password', 'Новый пароль'],
]

export function Layout() {
  const { user, ready, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  // Меню на телефоне: открыто для какого адреса — после перехода закрывается само
  const [menuAt, setMenuAt] = useState<string | null>(null)
  const menuOpen = menuAt === pathname

  // Фигурные скобки обязательны: в свежем Chrome scrollTo возвращает Promise,
  // и React пытается вызвать его как функцию очистки → «is not a function».
  useEffect(() => {
    window.scrollTo(0, 0)
    // Страницы чая, магазина и автора уточнят заголовок сами (usePageTitle), когда загрузятся
    const section = SECTION_TITLES.find(([prefix]) => pathname === prefix || pathname.startsWith(prefix + '/'))
    document.title = section ? `${section[1]} — 5 листов` : '5 листов — рейтинг чаёв по магазинам'
  }, [pathname])

  return (
    <>
      <div className="container">
        <header className="header">
          <Link to="/" className="logo" aria-label="5 листов — на главную">
            <img className="logo-mark" src="/favicon.svg" alt="" width={44} height={44} />
          </Link>
          <button
            type="button"
            className="btn btn-ghost btn-sm menu-toggle"
            aria-expanded={menuOpen}
            aria-controls="site-menu"
            onClick={() => setMenuAt(menuOpen ? null : pathname)}
          >
            {menuOpen ? 'Закрыть ✕' : 'Меню ☰'}
          </button>
          <div id="site-menu" className={menuOpen ? 'header-menu open' : 'header-menu'}>
          <nav className="nav" aria-label="Основное меню">
            <NavLink to="/teas">Чаи</NavLink>
            <NavLink to="/shops">Магазины</NavLink>
            <NavLink to="/rankings">Рейтинги</NavLink>
            {user && <NavLink to="/diary">Дневник</NavLink>}
          </nav>
          <div className="row" style={{ gap: 8, minHeight: 38, visibility: ready ? 'visible' : 'hidden' }}>
            <FeedbackButton className="btn btn-ghost btn-sm feedback-btn" />
            {user ? (
              <>
                <Link to="/profile" className="btn btn-ghost btn-sm">{user.name}</Link>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={async () => {
                    await logout()
                    navigate('/')
                  }}
                >
                  Выйти
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn btn-ghost btn-sm">Войти</Link>
                <Link to="/register" className="btn btn-sm">Регистрация</Link>
              </>
            )}
          </div>
          </div>
        </header>
        <main>
          <Outlet />
        </main>
        <footer className="footer">
          <span>© {new Date().getFullYear()} 5 листов — рейтинг чаёв по магазинам</span>
        </footer>
      </div>
    </>
  )
}

/** Обёртка для страниц только для авторизованных. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <Loading />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <>{children}</>
}

export function Loading() {
  return <div className="skeleton" style={{ height: 320, marginTop: 24 }} aria-busy="true" aria-label="Загрузка" />
}

export function NotFoundBlock({ text = 'Такой страницы нет' }: { text?: string }) {
  return (
    <div className="page">
      <PageHero
        center
        color="var(--butter)"
        eyebrow="404"
        title={text}
        lead="Возможно, чай уже закончился или ссылка устарела."
        stickers={[
          { text: 'улун?', style: { left: '8%', top: 48 } },
          { text: 'пуэр?', bg: 'var(--peach)', style: { right: '9%', top: 70 } },
        ]}
      >
        <Link to="/" className="btn">На главную</Link>
      </PageHero>
    </div>
  )
}
