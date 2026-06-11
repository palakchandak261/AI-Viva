import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { analyticsApi } from '../services/api'
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
  ResponsiveContainer, Tooltip, BarChart, Bar, Cell, XAxis, YAxis
} from 'recharts'
import {
  Trophy, ThumbsUp, AlertTriangle, ArrowLeft, BarChart2,
  ShieldAlert, ShieldCheck, Mic, TrendingUp, FileText, Star
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

export default function ResultsPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!sessionId) return
    analyticsApi.session(sessionId)
      .then(({ data }) => setData(data))
      .catch(() => toast.error('Could not load results.'))
      .finally(() => setLoading(false))
  }, [sessionId])

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <Spinner size="lg" />
      <p className="text-slate-500 text-sm">Loading your results...</p>
    </div>
  )
  if (!data) return (
    <div className="text-center mt-20">
      <p className="text-slate-500">Results not found.</p>
      <button onClick={() => navigate('/dashboard')} className="btn-secondary mt-4">Back</button>
    </div>
  )

  const { overall_score, analytics, performance_report, question_breakdown, avg_response_time, voice_summary } = data
  const grade = analytics?.grade ?? '—'
  const gradeGradient =
    grade === 'A' ? 'from-green-500 to-emerald-400' :
    grade === 'B' ? 'from-brand-500 to-violet-500' :
    grade === 'C' ? 'from-amber-500 to-orange-400' :
    'from-red-500 to-rose-500'

  const radarData = Object.entries(analytics?.topic_scores ?? {}).map(([topic, score]) => ({
    topic: topic.length > 14 ? topic.slice(0, 14) + '…' : topic,
    score: Number(score), fullMark: 100,
  }))

  const scoreData = question_breakdown?.map((q: any) => ({
    q: `Q${q.sequence}`, score: Number((q.score ?? 0).toFixed(1))
  })) ?? []

  const barColor = (s: number) => s >= 7 ? '#4ade80' : s >= 4 ? '#fbbf24' : '#f87171'

  return (
    <div className="max-w-3xl space-y-6 pb-10">

      {/* Back header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/dashboard')} className="btn-ghost p-2.5 rounded-xl bg-white/5 border border-white/10">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-xl font-bold text-white">Viva Results</h1>
          <p className="text-slate-500 text-sm">Detailed performance analysis</p>
        </div>
      </div>

      {/* ── Score hero ───────────────────────────────────────────────────── */}
      <div className="glass-card text-center py-8 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ background: `radial-gradient(circle at 50% 0%, ${grade === 'A' ? '#22c55e' : grade === 'B' ? '#6366f1' : '#f59e0b'}, transparent 70%)` }} />
        <div className={`inline-flex items-center justify-center w-24 h-24 rounded-full bg-gradient-to-br ${gradeGradient} mb-4 shadow-glow`}>
          <span className="text-5xl font-black text-white">{grade}</span>
        </div>
        <p className="text-5xl font-black text-white mb-1">{overall_score?.toFixed(1)}%</p>
        <p className="text-slate-400 mb-5">Overall Score</p>
        <div className="flex justify-center gap-6 text-sm">
          {[
            { label: 'Questions', value: data.total_answered },
            { label: 'Follow-ups', value: data.weak_count },
            { label: 'Avg Time', value: `${avg_response_time?.toFixed(0)}s` },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <p className="font-bold text-white text-lg">{value}</p>
              <p className="text-slate-500 text-xs">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Strengths / Weaknesses ───────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4">
        <div className="glass-card">
          <div className="flex items-center gap-2 mb-3">
            <ThumbsUp size={16} className="text-green-400" />
            <span className="font-semibold text-green-300 text-sm">Strengths</span>
          </div>
          <ul className="space-y-2">
            {(analytics?.strengths ?? []).length === 0
              ? <li className="text-slate-600 text-xs">No strengths identified</li>
              : (analytics?.strengths ?? []).map((s: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <Star size={12} className="text-green-400 mt-1 shrink-0" />{s}
                </li>
              ))}
          </ul>
        </div>
        <div className="glass-card">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={16} className="text-amber-400" />
            <span className="font-semibold text-amber-300 text-sm">Needs Work</span>
          </div>
          <ul className="space-y-2">
            {(analytics?.weaknesses ?? []).length === 0
              ? <li className="text-slate-600 text-xs">No weaknesses flagged</li>
              : (analytics?.weaknesses ?? []).map((w: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-amber-400 mt-0.5 shrink-0">◆</span>{w}
                </li>
              ))}
          </ul>
        </div>
      </div>

      {/* ── Voice Summary ────────────────────────────────────────────────── */}
      {voice_summary && (voice_summary.voice_answer_count ?? 0) > 0 && (
        <div className="glass-card">
          <div className="flex items-center gap-2 mb-4">
            <Mic size={16} className="text-brand-400" />
            <h2 className="font-semibold text-slate-200 text-sm">Voice Analysis Summary</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: 'Avg Confidence',  value: voice_summary.average_confidence_score  != null ? `${voice_summary.average_confidence_score}%` : 'N/A', good: (voice_summary.average_confidence_score ?? 0) >= 60 },
              { label: 'Avg Speech Rate', value: voice_summary.average_speech_rate_wpm   != null ? `${voice_summary.average_speech_rate_wpm} WPM` : 'N/A', good: true },
              { label: 'Suspicious',      value: `${voice_summary.suspicious_answer_count} / ${voice_summary.voice_answer_count}`, good: voice_summary.suspicious_answer_count === 0 },
              { label: 'Max Risk',        value: voice_summary.highest_cheat_risk_score  != null ? `${voice_summary.highest_cheat_risk_score}%` : 'N/A', good: (voice_summary.highest_cheat_risk_score ?? 0) < 30 },
            ].map(({ label, value, good }) => (
              <div key={label} className={`px-3 py-2.5 rounded-xl border text-center ${good ? 'bg-green-500/10 border-green-500/20' : 'bg-amber-500/10 border-amber-500/20'}`}>
                <p className={`font-bold text-base ${good ? 'text-green-300' : 'text-amber-300'}`}>{value}</p>
                <p className="text-xs text-slate-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
          {/* Overall integrity verdict */}
          <div className={`mt-3 flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${voice_summary.suspicious_answer_count === 0 ? 'bg-green-500/10 text-green-300' : 'bg-red-500/10 text-red-300'}`}>
            {voice_summary.suspicious_answer_count === 0
              ? <ShieldCheck size={14} />
              : <ShieldAlert size={14} />}
            {voice_summary.suspicious_answer_count === 0
              ? 'No integrity concerns detected across all voice answers.'
              : `${voice_summary.suspicious_answer_count} voice answer(s) flagged for integrity review.`}
          </div>
        </div>
      )}

      {/* ── Charts ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Radar — topic scores */}
        {radarData.length > 2 && (
          <div className="glass-card">
            <div className="flex items-center gap-2 mb-3">
              <BarChart2 size={15} className="text-brand-400" />
              <h2 className="font-semibold text-slate-200 text-sm">Topic Performance</h2>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
                <PolarGrid stroke="rgba(255,255,255,0.08)" />
                <PolarAngleAxis dataKey="topic" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <Radar name="Score" dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} strokeWidth={2} />
                <Tooltip content={<ChartTooltip />} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}
        {/* Bar — per-question scores */}
        {scoreData.length > 0 && (
          <div className="glass-card">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp size={15} className="text-brand-400" />
              <h2 className="font-semibold text-slate-200 text-sm">Score per Question</h2>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={scoreData} barSize={14}>
                <XAxis dataKey="q" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 10]} tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip content={({ active, payload, label }) =>
                  active && payload?.length
                    ? <div className="bg-dark-800 border border-white/10 rounded-xl px-3 py-2 text-xs"><p className="text-slate-400">{label}</p><p className="text-brand-400 font-bold">{payload[0].value}/10</p></div>
                    : null} />
                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                  {scoreData.map((e: any, i: number) => <Cell key={i} fill={barColor(e.score)} fillOpacity={0.85} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* ── Question Breakdown ───────────────────────────────────────────── */}
      <div className="glass-card">
        <h2 className="section-title">Question Breakdown</h2>
        <div className="space-y-2">
          {(question_breakdown ?? []).map((q: any) => (
            <div key={q.sequence} className="py-3 border-b border-white/5 last:border-0">
              <div className="flex items-start gap-3">
                <span className="text-xs font-mono font-bold text-slate-600 w-7 pt-0.5">Q{q.sequence}</span>
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="badge bg-blue-500/15 text-blue-400">{q.type}</span>
                    {q.is_weak && <span className="badge bg-amber-500/15 text-amber-400">Weak</span>}
                    {q.cheat_risk_level && q.cheat_risk_level !== 'Clean' && (
                      <span className="badge bg-red-500/15 text-red-400">⚠ {q.cheat_risk_level}</span>
                    )}
                    <span className="text-xs text-slate-500 truncate">{q.topic}</span>
                  </div>
                  {/* Confidence bar */}
                  {q.confidence_score != null && (
                    <div className="flex items-center gap-2">
                      <Mic size={11} className="text-slate-600 shrink-0" />
                      <span className="text-xs text-slate-600 w-16 shrink-0">Confidence</span>
                      <div className="flex-1 bg-white/5 rounded-full h-1.5">
                        <div className={`h-1.5 rounded-full transition-all ${q.confidence_score >= 65 ? 'bg-green-500' : q.confidence_score >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                          style={{ width: `${q.confidence_score}%` }} />
                      </div>
                      <span className="text-xs text-slate-500 w-8 text-right">{Math.round(q.confidence_score)}%</span>
                    </div>
                  )}
                  {/* Speech rate */}
                  {q.speech_rate_wpm != null && (
                    <p className="text-xs text-slate-600">Speech: {q.speech_rate_wpm?.toFixed(0)} WPM · Response: {q.response_time}s</p>
                  )}
                  {/* Cheat flags */}
                  {q.cheat_flags?.length > 0 && (
                    <div className="text-xs text-red-400/80 space-y-0.5">
                      {q.cheat_flags.slice(0, 2).map((f: any, i: number) => (
                        <p key={i}>• {f.detail}</p>
                      ))}
                    </div>
                  )}
                </div>
                <div className="shrink-0 text-right">
                  <span className={`text-lg font-black
                    ${(q.score ?? 0) >= 7 ? 'text-green-400' : (q.score ?? 0) >= 4 ? 'text-amber-400' : 'text-red-400'}`}>
                    {q.score?.toFixed(1) ?? '—'}
                  </span>
                  <p className="text-xs text-slate-600">/10</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── AI Report ────────────────────────────────────────────────────── */}
      {performance_report && (
        <div className="glass-card">
          <div className="flex items-center gap-2 mb-3">
            <Trophy size={16} className="text-amber-400" />
            <h2 className="font-semibold text-slate-200 text-sm">AI Examiner's Report</h2>
          </div>
          <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">{performance_report}</p>
        </div>
      )}

      {/* ── Recommendations ──────────────────────────────────────────────── */}
      {(analytics?.recommendations ?? []).length > 0 && (
        <div className="glass-card">
          <div className="flex items-center gap-2 mb-3">
            <FileText size={16} className="text-brand-400" />
            <h2 className="font-semibold text-slate-200 text-sm">Recommendations</h2>
          </div>
          <ul className="space-y-2">
            {analytics.recommendations.map((r: string, i: number) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-slate-300">
                <span className="w-5 h-5 rounded-full bg-brand-gradient flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5 shadow-glow-sm">{i+1}</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <button onClick={() => navigate('/dashboard')} className="btn-secondary flex-1 justify-center">
          Back to Dashboard
        </button>
        <button onClick={() => navigate('/analytics')} className="btn-primary flex-1 justify-center">
          View Analytics
        </button>
      </div>
    </div>
  )
}
