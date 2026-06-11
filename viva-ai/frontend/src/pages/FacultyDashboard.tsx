import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyticsApi } from '../services/api'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'
import {
  Users, TrendingUp, CheckCircle2, ShieldAlert, ShieldCheck,
  Search, Eye, Award, AlertTriangle, Mic
} from 'lucide-react'
import Spinner from '../components/ui/Spinner'
import toast from 'react-hot-toast'

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-dark-800 border border-white/10 rounded-xl px-3 py-2 text-xs shadow-card">
      <p className="text-slate-400 mb-0.5">{label}</p>
      <p className="text-brand-400 font-bold">{payload[0].value}%</p>
    </div>
  )
}

export default function FacultyDashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'score' | 'sessions' | 'name'>('score')

  useEffect(() => {
    analyticsApi.facultyOverview()
      .then(({ data }) => setData(data))
      .catch(() => toast.error('Failed to load faculty data.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <Spinner size="lg" />
      <p className="text-slate-500 text-sm">Loading faculty dashboard...</p>
    </div>
  )
  if (!data) return null

  const students: any[] = data.students ?? []

  const filtered = students
    .filter(s =>
      s.student_name.toLowerCase().includes(search.toLowerCase()) ||
      s.student_email.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'score')    return b.avg_score - a.avg_score
      if (sortBy === 'sessions') return b.total_sessions - a.total_sessions
      return a.student_name.localeCompare(b.student_name)
    })

  const chartData = [...students]
    .sort((a, b) => b.avg_score - a.avg_score)
    .slice(0, 12)
    .map(s => ({ name: s.student_name.split(' ')[0], score: s.avg_score }))

  const barColor = (s: number) => s >= 75 ? '#4ade80' : s >= 50 ? '#fbbf24' : '#f87171'

  const passing     = students.filter(s => s.avg_score >= 50).length
  const atRisk      = students.filter(s => s.avg_score > 0 && s.avg_score < 50).length
  const topStudents = students.filter(s => s.avg_score >= 80).length

  return (
    <div className="space-y-7 pb-8">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white mb-1">Faculty Panel</h1>
        <p className="text-slate-400 text-sm">Monitor student performance and integrity across all viva sessions.</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: 'Total Students', value: data.total_students,   icon: Users,        color: 'bg-blue-500/15 text-blue-400' },
          { label: 'Total Sessions', value: data.total_sessions,   icon: CheckCircle2, color: 'bg-purple-500/15 text-purple-400' },
          { label: 'Class Average',  value: `${data.class_avg_score}%`, icon: TrendingUp, color: 'bg-brand-500/15 text-brand-400' },
          { label: 'Top Performers', value: topStudents,           icon: Award,        color: 'bg-amber-500/15 text-amber-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <div className={`stat-icon ${color}`}><Icon size={18} /></div>
            <div>
              <p className="text-xl font-bold text-white">{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Status summary */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Passing (≥50%)',  value: passing,  color: 'bg-green-500/10 border-green-500/20 text-green-400' },
          { label: 'At Risk (<50%)',  value: atRisk,   color: 'bg-red-500/10 border-red-500/20 text-red-400' },
          { label: 'Top Scorers (≥80%)', value: topStudents, color: 'bg-amber-500/10 border-amber-500/20 text-amber-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className={`rounded-xl border px-4 py-3 text-center ${color}`}>
            <p className="text-2xl font-black">{value}</p>
            <p className="text-xs opacity-80 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Bar chart */}
      {chartData.length > 0 && (
        <div className="glass-card">
          <h2 className="section-title">Student Performance (Top 12 by Score)</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} barSize={18}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} unit="%" axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                {chartData.map((e, i) => <Cell key={i} fill={barColor(e.score)} fillOpacity={0.85} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Student list */}
      <div className="glass-card">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="section-title mb-0">All Students ({students.length})</h2>
          <div className="flex items-center gap-3">
            {/* Search */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                className="input pl-9 py-2 text-xs w-48"
                placeholder="Search student..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            {/* Sort */}
            <select
              className="input py-2 text-xs w-36"
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
            >
              <option value="score">Sort: Score</option>
              <option value="sessions">Sort: Sessions</option>
              <option value="name">Sort: Name</option>
            </select>
          </div>
        </div>

        {filtered.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">No students match your search.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[600px]">
              <thead>
                <tr className="border-b border-white/5 text-left">
                  {['Student', 'Email', 'Sessions', 'Avg Score', 'Integrity', 'Actions'].map(h => (
                    <th key={h} className="pb-3 text-xs font-semibold text-slate-500 uppercase tracking-wide pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filtered.map((s) => {
                  const scoreColor = s.avg_score >= 75 ? 'text-green-400' : s.avg_score >= 50 ? 'text-amber-400' : 'text-red-400'
                  return (
                    <tr key={s.student_id} className="hover:bg-white/2 transition-colors">
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-lg bg-brand-gradient flex items-center justify-center text-white text-xs font-bold shadow-glow-sm">
                            {s.student_name[0].toUpperCase()}
                          </div>
                          <span className="font-medium text-slate-200">{s.student_name}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-slate-500 text-xs">{s.student_email}</td>
                      <td className="py-3 pr-4 text-center">
                        <span className="badge bg-purple-500/15 text-purple-400">{s.total_sessions}</span>
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-white/5 rounded-full h-1.5 w-16">
                            <div className={`h-1.5 rounded-full ${s.avg_score >= 75 ? 'bg-green-500' : s.avg_score >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                              style={{ width: `${s.avg_score}%` }} />
                          </div>
                          <span className={`font-bold text-sm ${scoreColor}`}>{s.avg_score}%</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        {/* Check for suspicious flags across sessions — safely */}
                        {(() => {
                          const flagged = (s.sessions ?? []).some((ss: any) =>
                            ss.cheat_risk === 'High Risk' || ss.suspicious_count > 0
                          )
                          return flagged
                            ? <div className="flex items-center gap-1 text-xs text-red-400"><ShieldAlert size={12} /> Flagged</div>
                            : <div className="flex items-center gap-1 text-xs text-green-400"><ShieldCheck size={12} /> Clean</div>
                        })()}
                      </td>
                      <td className="py-3">
                        <div className="flex items-center gap-1.5">
                          {(s.sessions ?? []).slice(0, 3).map((ss: any, idx: number) => (
                            <button key={idx} onClick={() => navigate(`/results/${ss.session_id}`)}
                              className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-white/5 text-slate-400 hover:bg-brand-500/15 hover:text-brand-300 border border-white/10 transition-all duration-200">
                              <Eye size={11} />
                              {idx === 0 ? 'Latest' : `#${idx + 1}`}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* At-risk alert */}
      {atRisk > 0 && (
        <div className="flex items-start gap-3 px-4 py-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
          <AlertTriangle size={18} className="text-amber-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-amber-300 font-semibold">{atRisk} student{atRisk > 1 ? 's' : ''} at risk</p>
            <p className="text-amber-400/70 text-sm mt-1">
              These students are scoring below 50%. Consider scheduling additional support sessions.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
