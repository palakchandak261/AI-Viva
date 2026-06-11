import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { BrainCircuit, Mail, Lock, ArrowRight, Sparkles } from 'lucide-react'
import { authApi } from '../services/api'
import { useAuthStore } from '../store/authStore'
import Spinner from '../components/ui/Spinner'

export default function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authApi.login(email, password)
      setAuth(data.access_token, { id: data.user_id, name: data.name, email: data.email, role: data.role })
      // Route by role
      if (data.role === 'faculty' || data.role === 'admin') {
        navigate('/faculty')
      } else {
        navigate('/dashboard')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Invalid email or password.')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-dark-950 flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-hero-gradient" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-600/10 rounded-full blur-3xl" />

      <div className="relative w-full max-w-md z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-gradient shadow-glow mb-4 animate-float">
            <BrainCircuit size={30} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-1">AI Viva Examiner</h1>
          <p className="text-slate-400 text-sm">Sign in to your account</p>
        </div>

        {/* Form */}
        <div className="glass-card">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="label">Email address</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input className="input pl-10" type="email" value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com" required autoFocus />
              </div>
            </div>
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input className="input pl-10" type="password" value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••" required />
              </div>
            </div>
            <button type="submit" className="btn-primary w-full justify-center py-3" disabled={loading}>
              {loading ? <Spinner size="sm" /> : <><span>Sign In</span><ArrowRight size={16} /></>}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-white/10 text-center">
            <p className="text-sm text-slate-500">
              No account?{' '}
              <Link to="/register" className="text-brand-400 hover:text-brand-300 font-semibold transition-colors">
                Create one free
              </Link>
            </p>
          </div>
        </div>

        {/* Features teaser */}
        <div className="mt-6 flex justify-center gap-6 text-xs text-slate-600">
          {['AI Questions', 'Voice Analysis', 'Cheat Detection'].map(f => (
            <div key={f} className="flex items-center gap-1.5">
              <Sparkles size={11} className="text-brand-600" />
              {f}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
