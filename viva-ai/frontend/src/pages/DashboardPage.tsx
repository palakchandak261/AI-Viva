import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { submissionsApi, vivaApi } from '../services/api'
import { useAuthStore } from '../store/authStore'
import { Upload, PlayCircle, Trophy, Clock, FileText, Folder, Zap, ArrowRight, CheckCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import Spinner from '../components/ui/Spinner'

interface Submission { id: string; title: string; created_at: string; has_report: boolean; has_ppt: boolean; has_code: boolean }
interface Session { id: string; status: string; overall_score: number | null; created_at: string; difficulty_level: string }

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([submissionsApi.list(), vivaApi.listSessions()])
      .then(([sub, ses]) => { setSubmissions(sub.data); setSessions(ses.data) })
      .catch(() => toast.error('Failed to load dashboard data.'))
      .finally(() => setLoading(false))
  }, [])

  const startViva = async (submissionId: string) => {
    setStarting(submissionId)
    try {
      const { data } = await vivaApi.start({ submission_id: submissionId, total_questions: 10, difficulty_level: 'medium' })
      navigate(`/viva/${data.session_id}`, { state: { firstExchange: data.first_exchange, totalQuestions: data.total_questions, projectTitle: data.project_title } })
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to start viva.')
    } finally { setStarting(null) }
  }

  const completedSessions = sessions.filter(s => s.status === 'completed')
  const bestScore = completedSessions.length ? Math.max(...completedSessions.map(s => s.overall_score ?? 0)) : null

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center gap-3">
        <Spinner size="lg" />
        <p className="text-slate-500 text-sm">Loading your dashboard...</p>
      </div>
    </div>
  )

  return (
    <div className="space-y-8">
      {/* Hero header */}
      <div className="relative overflow-hidden rounded-2xl bg-brand-gradient p-6 shadow-glow">
        <div className="absolute inset-0 opacity-20" style={{backgroundImage: 'radial-gradient(circle at 70% 50%, white 0%, transparent 60%)'}} />
        <div className="relative">
          <p className="text-brand-200 text-sm font-medium mb-1">Welcome back</p>
          <h1 className="text-2xl font-bold text-white mb-1">{user?.name} 👋</h1>
          <p className="text-brand-200 text-sm">Ready for your next viva examination?</p>
        </div>
        <div className="absolute right-6 top-1/2 -translate-y-1/2 opacity-20">
          <Zap size={80} className="text-white" />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Projects', value: submissions.length, icon: Folder, color: 'bg-blue-500/15 text-blue-400' },
          { label: 'Viva Sessions', value: sessions.length, icon: PlayCircle, color: 'bg-purple-500/15 text-purple-400' },
          { label: 'Best Score', value: bestScore !== null ? `${bestScore.toFixed(0)}%` : '—', icon: Trophy, color: 'bg-amber-500/15 text-amber-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <div className={`stat-icon ${color}`}><Icon size={20} /></div>
            <div>
              <p className="text-2xl font-bold text-white">{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Projects */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title mb-0">Your Projects</h2>
          <button onClick={() => navigate('/upload')} className="btn-primary text-xs px-4 py-2">
            <Upload size={14} /> Upload New
          </button>
        </div>

        {submissions.length === 0 ? (
          <div className="glass-card text-center py-14">
            <div className="w-14 h-14 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-4">
              <Upload size={24} className="text-slate-500" />
            </div>
            <p className="text-slate-300 font-semibold mb-1">No projects yet</p>
            <p className="text-slate-500 text-sm mb-5">Upload your project report, slides, or source code to get started</p>
            <button onClick={() => navigate('/upload')} className="btn-primary">
              Upload your first project
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {submissions.map((sub) => (
              <div key={sub.id} className="glass-card flex items-center justify-between hover:border-brand-500/20 transition-all duration-200">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-brand-500/15 flex items-center justify-center">
                    <FileText size={18} className="text-brand-400" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-200">{sub.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Clock size={11} className="text-slate-600" />
                      <span className="text-xs text-slate-600">{new Date(sub.created_at).toLocaleDateString()}</span>
                      {sub.has_report && <span className="badge bg-red-500/15 text-red-400">PDF</span>}
                      {sub.has_ppt && <span className="badge bg-orange-500/15 text-orange-400">PPT</span>}
                      {sub.has_code && <span className="badge bg-green-500/15 text-green-400">Code</span>}
                    </div>
                  </div>
                </div>
                <button onClick={() => startViva(sub.id)} disabled={starting === sub.id} className="btn-primary text-sm">
                  {starting === sub.id ? <Spinner size="sm" /> : <><PlayCircle size={15} /> Start Viva</>}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Sessions */}
      {sessions.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title mb-0">Recent Sessions</h2>
            <button onClick={() => navigate('/analytics')} className="btn-ghost text-xs">
              View All <ArrowRight size={12} />
            </button>
          </div>
          <div className="space-y-2">
            {sessions.slice(0, 5).map((ses) => (
              <div key={ses.id} className="glass-card flex items-center justify-between py-4">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center
                    ${ses.status === 'completed' ? 'bg-green-500/15' : 'bg-amber-500/15'}`}>
                    {ses.status === 'completed'
                      ? <CheckCircle size={16} className="text-green-400" />
                      : <AlertCircle size={16} className="text-amber-400" />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`badge capitalize
                        ${ses.status === 'completed' ? 'bg-green-500/15 text-green-400'
                          : ses.status === 'in_progress' ? 'bg-amber-500/15 text-amber-400'
                          : 'bg-slate-500/15 text-slate-400'}`}>
                        {ses.status.replace('_', ' ')}
                      </span>
                      <span className="badge bg-white/5 text-slate-400 capitalize">{ses.difficulty_level}</span>
                    </div>
                    <p className="text-xs text-slate-600 mt-1">{new Date(ses.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {ses.overall_score !== null && (
                    <span className={`text-xl font-bold ${ses.overall_score >= 75 ? 'text-green-400' : ses.overall_score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                      {ses.overall_score.toFixed(0)}%
                    </span>
                  )}
                  {ses.status === 'completed' && (
                    <button onClick={() => navigate(`/results/${ses.id}`)} className="btn-secondary text-xs px-3 py-1.5">
                      View Report
                    </button>
                  )}
                  {ses.status === 'in_progress' && (
                    <button onClick={() => navigate(`/viva/${ses.id}`)} className="btn-primary text-xs px-3 py-1.5">
                      Continue
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
