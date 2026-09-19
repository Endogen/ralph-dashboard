import { lazy, Suspense } from "react"
import { Navigate, Route, Routes, useLocation } from "react-router-dom"

import { AppLayout } from "@/components/layout/app-layout"
const ArchivePage = lazy(() => import("@/components/layout/archive-page").then((module) => ({ default: module.ArchivePage })))
const DashboardPage = lazy(() => import("@/components/layout/dashboard-page").then((module) => ({ default: module.DashboardPage })))
import { LoginPage } from "@/components/layout/login-page"
const ProjectPage = lazy(() => import("@/components/layout/project-page").then((module) => ({ default: module.ProjectPage })))
const WizardPage = lazy(() => import("@/components/wizard/wizard-page").then((module) => ({ default: module.WizardPage })))
import { useAuthStore } from "@/stores/auth-store"

function RequireAuth() {
  const accessToken = useAuthStore((state) => state.accessToken)
  const location = useLocation()

  if (!accessToken) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <AppLayout />
}

function LoginRoute() {
  const accessToken = useAuthStore((state) => state.accessToken)
  if (accessToken) {
    return <Navigate to="/" replace />
  }
  return <LoginPage />
}

export function App() {
  return (
    <Suspense fallback={<p role="status" className="p-6">Loading…</p>}>
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/" element={<RequireAuth />}>
        <Route index element={<DashboardPage />} />
        <Route path="wizard" element={<WizardPage />} />
        <Route path="archive" element={<ArchivePage />} />
        <Route path="project/:id/*" element={<ProjectPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  )
}
