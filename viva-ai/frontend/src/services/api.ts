import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({ baseURL: '/api' })

// Attach token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { name: string; email: string; password: string; role?: string }) =>
    api.post('/auth/register', data),

  login: (email: string, password: string) => {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    return api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
}

// ── Submissions ───────────────────────────────────────────────────────────────
export const submissionsApi = {
  upload: (formData: FormData) =>
    api.post('/submissions/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  list: () => api.get('/submissions/'),

  get: (id: string) => api.get(`/submissions/${id}`),
}

// ── Viva ──────────────────────────────────────────────────────────────────────
export const vivaApi = {
  start: (payload: { submission_id: string; total_questions: number; difficulty_level: string }) =>
    api.post('/viva/start', payload),

  submitAnswer: (payload: {
    session_id: string
    exchange_id: string
    student_answer: string
    response_time_seconds: number
  }) => api.post('/viva/answer', payload),

  getSession: (sessionId: string) => api.get(`/viva/${sessionId}`),

  listSessions: () => api.get('/viva/'),
}

// ── Analytics ────────────────────────────────────────────────────────────────
export const analyticsApi = {
  me: () => api.get('/analytics/me'),
  session: (sessionId: string) => api.get(`/analytics/session/${sessionId}`),
  facultyOverview: () => api.get('/analytics/faculty/overview'),
}

// ── Users ─────────────────────────────────────────────────────────────────────
export const usersApi = {
  me: () => api.get('/users/me'),
}

// ── Voice ─────────────────────────────────────────────────────────────────────
export const voiceApi = {
  transcribe: (formData: FormData) =>
    api.post('/voice/transcribe', formData),

  submitVoiceAnswer: (formData: FormData) =>
    api.post('/voice/submit-voice-answer', formData),
}

export default api
