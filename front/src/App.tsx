import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { AuthProvider } from './auth/AuthContext'
import { AddTea } from './pages/AddTea'
import { AuthorPage } from './pages/AuthorPage'
import { Layout, NotFoundBlock, RequireAuth } from './components/Layout'
import { Login, Register } from './pages/Auth'
import { Diary } from './pages/Diary'
import { Home } from './pages/Home'
import { ProducerPage } from './pages/ProducerPage'
import { Producers } from './pages/Producers'
import { Profile } from './pages/Profile'
import { CategoryRanking, LegacyRedirect, ProducerRanking, RankingsLayout, TeaRanking } from './pages/Rankings'
import { TeaPage } from './pages/TeaPage'
import { Teas } from './pages/Teas'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="teas" element={<Teas />} />
            <Route path="teas/new" element={<RequireAuth><AddTea /></RequireAuth>} />
            <Route path="teas/:id" element={<TeaPage />} />
            <Route path="shops" element={<Producers />} />
            <Route path="shops/:id" element={<ProducerPage />} />
            <Route path="rankings" element={<RankingsLayout />}>
              <Route index element={<Navigate to="teas" replace />} />
              <Route path="categories" element={<CategoryRanking />} />
              <Route path="categories/:category" element={<CategoryRanking />} />
              <Route path="shops" element={<ProducerRanking />} />
              <Route path="teas" element={<TeaRanking />} />
            </Route>
            {/* старые адреса */}
            <Route path="producers" element={<LegacyRedirect to={() => '/shops'} />} />
            <Route path="producers/:id" element={<LegacyRedirect to={(p) => `/shops/${p.id}`} />} />
            <Route path="rankings/producers" element={<LegacyRedirect to={() => '/rankings/shops'} />} />
            <Route path="where-to-buy" element={<LegacyRedirect to={() => '/rankings/categories'} />} />
            <Route path="where-to-buy/:category" element={<LegacyRedirect to={(p) => `/rankings/categories/${p.category}`} />} />
            <Route path="login" element={<Login />} />
            <Route path="register" element={<Register />} />
            <Route path="diary" element={<RequireAuth><Diary /></RequireAuth>} />
            <Route path="profile" element={<RequireAuth><Profile /></RequireAuth>} />
            <Route path="users/:id" element={<AuthorPage />} />
            <Route path="*" element={<NotFoundBlock />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
