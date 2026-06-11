import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'

// Pages
import LoginPage      from './pages/LoginPage'
import RegisterPage   from './pages/RegisterPage'
import DashboardPage  from './pages/DashboardPage'
import UploadPage     from './pages/UploadPage'
import VivaPage       from './pages/VivaPage'
import ResultsPage    from './pages/ResultsPage'
import AnalyticsPage  from './pages/AnalyticsPage'
import FacultyDashboard from './pages/FacultyDashboard'
import Layout         from './components/Layout'

// ── Guards ────────────────────────────────────────────────────────────────────

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

/** Redirect to the correct home page based on role */
function HomeRedirect() {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'faculty' || user.role === 'admin') {
    return <Navigate to="/faculty" replace />
  }
  return <Navigate to="/dashboard" replace />
}

/** Only faculty / admin can access this route */
function FacultyRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'faculty' && user.role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}

/** Only students can access this route */
function StudentRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'faculty') return <Navigate to="/faculty" replace />
  return <>{children}</>
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login"    element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected — all inside Layout */}
      <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>

        {/* Smart home redirect based on role */}
        <Route index element={<HomeRedirect />} />

        {/* Student-only pages */}
        <Route path="dashboard" element={<StudentRoute><DashboardPage /></StudentRoute>} />
        <Route path="upload"    element={<StudentRoute><UploadPage /></StudentRoute>} />
        <Route path="analytics" element={<StudentRoute><AnalyticsPage /></StudentRoute>} />
        <Route path="viva/:sessionId"    element={<StudentRoute><VivaPage /></StudentRoute>} />

        {/* Results — both roles can view (faculty views student reports) */}
        <Route path="results/:sessionId" element={<PrivateRoute><ResultsPage /></PrivateRoute>} />

        {/* Faculty-only */}
        <Route path="faculty" element={<FacultyRoute><FacultyDashboard /></FacultyRoute>} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<HomeRedirect />} />
    </Routes>
  )
}
