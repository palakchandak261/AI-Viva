import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { BrainCircuit, Mail, Lock, User, ArrowRight } from 'lucide-react'
import { authApi } from '../services/api'
import { useAuthStore } from '../store/authStore'
import Spinner from '../components/ui/Spinner'

export default function RegisterPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'student' | 'faculty'>('student')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (password.length < 8) { toast.error('Password must be at least 8 characters.'); return }
    setLoading(true)
    try {
      const { data } = await authApi.register({ name, email, password, role })
      setAuth(data.access_token, { id: data.user_id, name: data.name, email: data.email, role: data.role })
      if (data.role === 'faculty' || data.role === 'admin') {
        navigate('/faculty')
      } else {
        navigate('/dashboard')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Registration failed.')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-dark-950 flex items-center justify-center px-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-hero-gradient" />
      <div className="absolute top-1/3 right-1/3 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl" />
      <div className="absolute bottom-1/3 left-1/3 w-80 h-80 bg-brand-600/10 rounded-full blur-3xl" />

      <div className="relative w-full max-w-md z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-gradient shadow-glow mb-4">
            <BrainCircuit size={30} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-1">Create Account</h1>
          <p className="text-slate-400 text-sm">Join AI Viva Examiner today</p>
        </div>

        <div className="glass-card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Full Name</label>
              <div className="relative">
                <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input className="input pl-10" value={name} onChange={e => setName(e.target.value)}
                  placeholder="John Doe" required />
              </div>
            </div>
            <div>
              <label className="label">Email address</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input className="input pl-10" type="email" value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com" required />
              </div>
            </div>
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                <input className="input pl-10" type="password" value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters" required />
              </div>
            </div>
            <div>
              <label className="label">I am a</label>
              <div className="grid grid-cols-2 gap-3">
                {(['student', 'faculty'] as const).map(r => (
                  <button type="button" key={r} onClick={() => setRole(r)}
                    className={`py-2.5 px-4 rounded-xl text-sm font-semibold border transition-all duration-200 capitalize
                      ${role === r
                        ? 'bg-brand-gradient text-white border-transparent shadow-glow-sm'
                        : 'bg-white/5 text-slate-400 border-white/10 hover:bg-white/10 hover:text-slate-200'
                      }`}>
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <button type="submit" className="btn-primary w-full justify-center py-3 mt-2" disabled={loading}>
              {loading ? <Spinner size="sm" /> : <><span>Create Account</span><ArrowRight size={16} /></>}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-white/10 text-center">
            <p className="text-sm text-slate-500">
              Already have an account?{' '}
              <Link to="/login" className="text-brand-400 hover:text-brand-300 font-semibold transition-colors">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
