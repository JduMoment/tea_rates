import { useEffect, type ReactNode } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../auth/AuthContext'
import { PageHero } from './PageHero'

export function Layout() {
  const { user, ready, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  // Фигурные скобки обязательны: в свежем Chrome scrollTo возвращает Promise,
  // и React пытается вызвать его как функцию очистки → «is not a function».
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <>
      <div className="container">
        <header className="header">
          <Link to="/" className="logo">
            <img className="logo-mark" src="/favicon.svg" alt="" width={40} height={40} />
            лист
          </Link>
          <nav className="nav" aria-label="Основное меню">
            <NavLink to="/teas">Чаи</NavLink>
            <NavLink to="/shops">Магазины</NavLink>
            <NavLink to="/rankings">Рейтинги</NavLink>
            {user && <NavLink to="/diary">Дневник</NavLink>}
          </nav>
          <div className="row" style={{ gap: 8, minHeight: 38, visibility: ready ? 'visible' : 'hidden' }}>
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
        </header>
        <main>
          <Outlet />
        </main>
        <footer className="footer">
          <span>© {new Date().getFullYear()} лист — рейтинг чаёв по магазинам</span>
          <span>Демо-данные · оценки вымышленные</span>
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
