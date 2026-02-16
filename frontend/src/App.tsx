import { Navigate, Route, Routes, useLocation } from "react-router-dom"

import { AppLayout } from "@/components/layout/app-layout"
import { ArchivePage } from "@/components/layout/archive-page"
import { DashboardPage } from "@/components/layout/dashboard-page"
import { LoginPage } from "@/components/layout/login-page"
import { ProjectPage } from "@/components/layout/project-page"
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
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/" element={<RequireAuth />}>
        <Route index element={<DashboardPage />} />
        <Route path="archive" element={<ArchivePage />} />
        <Route path="project/:id/*" element={<ProjectPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
