import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ROUTES } from '@/constants/app'
import { ProtectedRoute }  from './ProtectedRoute'
import { AppLayout }       from '@/components/layout/AppLayout'
import { AuthLayout }      from '@/components/layout/AuthLayout'
import { LandingPage }     from '@/pages/LandingPage'
import { LoginPage }       from '@/pages/auth/LoginPage'
import { RegisterPage }    from '@/pages/auth/RegisterPage'
import { ForgotPage }      from '@/pages/auth/ForgotPage'
import { DashboardPage }   from '@/pages/DashboardPage'
import { AnalyzePage }     from '@/pages/AnalyzePage'
import { ResultsPage }     from '@/pages/ResultsPage'
import { CitationsPage }   from '@/pages/CitationsPage'
import { ReportsPage }     from '@/pages/ReportsPage'
import { DocumentsPage }   from '@/pages/DocumentsPage'
import { SettingsPage }    from '@/pages/SettingsPage'
import { AboutPage }       from '@/pages/AboutPage'
import { NotFoundPage }    from '@/pages/NotFoundPage'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path={ROUTES.HOME}  element={<LandingPage />} />

        <Route element={<AuthLayout />}>
          <Route path={ROUTES.LOGIN}    element={<LoginPage />} />
          <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
          <Route path={ROUTES.FORGOT}   element={<ForgotPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path={ROUTES.DASHBOARD} element={<DashboardPage />} />
            <Route path={ROUTES.ANALYZE}   element={<AnalyzePage />} />
            <Route path={ROUTES.RESULTS}   element={<ResultsPage />} />
            <Route path={ROUTES.CITATIONS} element={<CitationsPage />} />
            <Route path={ROUTES.REPORTS}   element={<ReportsPage />} />
            <Route path={ROUTES.DOCUMENTS} element={<DocumentsPage />} />
            <Route path={ROUTES.SETTINGS}  element={<SettingsPage />} />
            <Route path={ROUTES.ABOUT}     element={<AboutPage />} />
          </Route>
        </Route>

        <Route path={ROUTES.NOT_FOUND} element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}