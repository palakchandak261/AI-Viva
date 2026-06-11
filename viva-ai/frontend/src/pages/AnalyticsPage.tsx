import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyticsApi } from '../services/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts'
import { TrendingUp, Target, Award, ArrowRight } from 'lucide-react'
import Spinner from '../components/ui/Spinner'
import toast from 'react-hot-toast'

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-dark-800 border border-white/10 rounded-xl px-3 py-2 text-xs shadow-card">
      <p className="text-slate-400">{label}</p>
      <p className="text-brand-400 font-bold">{payload[0].value}%</p>
    </div>
  )
}

export default function AnalyticsPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    analyticsApi.me()
      .then(({ data }) => setData(data))
      .catch(() => toast.error('Failed to load analytics.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center mt-20"><Spinner size="lg" /></div>

  if (!data || data.message) return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
        <Target size={28} className="text-slate-600" />
      </div>
      <p className="text-slate-300 font-semibold mb-1">No analytics yet</p>
      <p className="text-slate-500 text-sm mb-5">Complete a viva session to see your performance data</p>
      <button onClick={() => navigate('/dashboard')} className="btn-primary">Go to Dashboard</button>
    </div>
  )

  const trendData = data.score_trend?.map((t: any, i: number) => ({ session: `S${i+1}`, score: Number(t.score?.toFixed(1)), date: new Date(t.date).toLocaleDateString() }))
  const topicData = Object.entries(data.topic_averages ?? {}).map(([topic, score]) => ({ topic: topic.length > 14 ? topic.slice(0, 14) + '…' : topic, score: Number(score) }))
  const barColor = (s: number) => s >= 75 ? '#4ade80' : s >= 50 ? '#fbbf24' : '#f87171'

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white mb-1">My Analytics</h1>
        <p className="text-slate-400 text-sm">Your performance across all viva sessions</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Sessions Done', value: data.total_sessions, icon: Target, color: 'bg-purple-500/15 text-purple-400' },
          { label: 'Average Score', value: `${data.average_score}%`, icon: TrendingUp, color: 'bg-brand-500/15 text-brand-400' },
          { label: 'Best Score', value: `${data.best_score?.toFixed(0)}%`, icon: Award, color: 'bg-amber-500/15 text-amber-400' },
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

      {/* Score trend */}
      {trendData?.length > 1 && (
        <div className="glass-card">
          <h2 className="section-title">Score Trend</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="session" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} unit="%" axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={2.5} dot={{ r: 4, fill: '#6366f1', strokeWidth: 0 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Topic breakdown */}
      {topicData.length > 0 && (
        <div className="glass-card">
          <h2 className="section-title">Average Score by Topic</h2>
          <ResponsiveContainer width="100%" height={Math.max(180, topicData.length * 36)}>
            <BarChart data={topicData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} unit="%" axisLine={false} tickLine={false} />
              <YAxis dataKey="topic" type="category" tick={{ fontSize: 11, fill: '#94a3b8' }} width={110} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="score" radius={[0, 6, 6, 0]}>
                {topicData.map((e, i) => <Cell key={i} fill={barColor(e.score)} fillOpacity={0.8} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent sessions */}
      <div className="glass-card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title mb-0">Recent Sessions</h2>
          <button onClick={() => navigate('/dashboard')} className="btn-ghost text-xs">
            Dashboard <ArrowRight size={12} />
          </button>
        </div>
        <div className="space-y-2">
          {data.recent_sessions?.map((s: any) => (
            <div key={s.id} className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
              <div>
                <p className="text-sm font-semibold text-slate-200">{s.score?.toFixed(1)}%</p>
                <p className="text-xs text-slate-600">{new Date(s.completed_at).toLocaleString()}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xl font-black
                  ${s.analytics?.grade === 'A' ? 'text-green-400' : s.analytics?.grade === 'B' ? 'text-brand-400' : s.analytics?.grade === 'C' ? 'text-amber-400' : 'text-red-400'}`}>
                  {s.analytics?.grade}
                </span>
                <button onClick={() => navigate(`/results/${s.id}`)} className="btn-secondary text-xs px-3 py-1.5">View</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
