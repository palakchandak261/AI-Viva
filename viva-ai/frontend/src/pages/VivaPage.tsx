import { useState, useEffect, useRef } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Clock, AlertCircle, CheckCircle2, BrainCircuit,
  ShieldAlert, TrendingUp, Volume2, BookOpen
} from 'lucide-react'
import { voiceApi } from '../services/api'
import Spinner from '../components/ui/Spinner'
import VoiceRecorder from '../components/VoiceRecorder'

interface Exchange {
  id: string
  sequence_number: number
  question: string
  question_type: string
  topic: string
  difficulty: string
}

const DIFF_STYLE: Record<string, string> = {
  easy:   'bg-green-500/15 text-green-400 border-green-500/20',
  medium: 'bg-amber-500/15 text-amber-400 border-amber-500/20',
  hard:   'bg-red-500/15   text-red-400   border-red-500/20',
}
const TYPE_STYLE: Record<string, string> = {
  conceptual: 'bg-blue-500/15   text-blue-400',
  decision:   'bg-purple-500/15 text-purple-400',
  code:       'bg-teal-500/15   text-teal-400',
  scenario:   'bg-orange-500/15 text-orange-400',
  probe:      'bg-pink-500/15   text-pink-400',
}

export default function VivaPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const st = location.state as { firstExchange?: Exchange; totalQuestions?: number; projectTitle?: string } | null

  const [exchange, setExchange]     = useState<Exchange | null>(st?.firstExchange ?? null)
  const [totalQ,   setTotalQ]       = useState(st?.totalQuestions ?? 10)
  const [title]                     = useState(st?.projectTitle ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [isFollowUp, setIsFollowUp] = useState(false)
  const [loadingSession, setLoading]= useState(!st?.firstExchange)
  const [lastEval,  setLastEval]    = useState<any>(null)
  const [lastVoice, setLastVoice]   = useState<any>(null)
  const [answered,  setAnswered]    = useState(0)
  const [countdown, setCountdown]   = useState(5)
  const [voiceReady, setVoiceReady] = useState(false)

  const startRef  = useRef(Date.now())
  const prepRef   = useRef<number | null>(null)
  const recordRef = useRef<number | null>(null)

  // Load session if no state (direct URL navigation)
  useEffect(() => {
    if (!exchange && sessionId) {
      import('../services/api').then(({ vivaApi }) => {
        vivaApi.getSession(sessionId)
          .then(({ data }) => {
            setTotalQ(data.total_questions)
            if (data.status === 'completed') { navigate(`/results/${sessionId}`); return }
            const ua = data.exchanges.find((e: any) => !e.student_answer)
            if (ua) setExchange(ua)
            setAnswered(data.exchanges.filter((e: any) => e.student_answer).length)
          })
          .catch(() => toast.error('Session not found.'))
          .finally(() => setLoading(false))
      })
    } else { setLoading(false) }
  }, [])

  // Reset countdown on each new question
  useEffect(() => {
    if (!exchange) return
    startRef.current = Date.now()
    prepRef.current  = null
    recordRef.current= null
    setVoiceReady(false)
    setCountdown(5)
  }, [exchange?.id])

  // Countdown tick
  useEffect(() => {
    if (countdown <= 0) {
      prepRef.current = Date.now()
      setVoiceReady(true)
      return
    }
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown])

  const handleResult = (data: any) => {
    setAnswered(c => c + 1)
    setLastEval(data.evaluation ?? null)
    setLastVoice(data.voice_analysis ?? null)

    if (data.status === 'completed') {
      toast.success('Viva completed! Generating your report...')
      setTimeout(() => navigate(`/results/${sessionId}`), 1500)
      return
    }
    if (data.next_exchange) {
      setIsFollowUp(data.is_followup)
      setExchange(data.next_exchange)
    }
  }

  const handleVoiceReady = async (blob: Blob) => {
    if (!exchange || !sessionId) return
    setSubmitting(true)
    const rt = Math.floor((Date.now() - startRef.current) / 1000)
    const delay = (prepRef.current && recordRef.current)
      ? Math.max(0, Math.floor((recordRef.current - prepRef.current) / 1000))
      : 0
    try {
      const fd = new FormData()
      const ext = blob.type.split('/')[1]?.split(';')[0] || 'webm'
      fd.append('audio',                  blob, `answer.${ext}`)
      fd.append('session_id',             sessionId)
      fd.append('exchange_id',            exchange.id)
      fd.append('response_time_seconds',  String(rt))
      fd.append('start_delay_seconds',    String(delay))
      fd.append('question',               exchange.question)
      const { data } = await voiceApi.submitVoiceAnswer(fd)
      handleResult(data)
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Voice submission failed.'
      if (msg.includes('configured') || msg.includes('GROQ')) {
        toast.error('Voice service not configured — add GROQ_API_KEY to your .env file', { duration: 6000 })
      } else if (msg.includes('speech detected')) {
        toast.error('No speech detected. Please speak clearly and try again.')
      } else {
        toast.error(msg)
      }
    } finally { setSubmitting(false) }
  }

  const progress = totalQ > 0 ? Math.round((answered / totalQ) * 100) : 0

  if (loadingSession) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <Spinner size="lg" />
      <p className="text-slate-500 text-sm">Loading your viva session...</p>
    </div>
  )

  if (!exchange) return (
    <div className="text-center mt-20">
      <BrainCircuit size={40} className="mx-auto text-slate-600 mb-3" />
      <p className="text-slate-400 mb-4">No active question found.</p>
      <button onClick={() => navigate('/dashboard')} className="btn-secondary">Back to Dashboard</button>
    </div>
  )

  const cheat = lastVoice?.cheat_detection

  return (
    <div className="max-w-2xl mx-auto space-y-5 pb-8">

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-gradient flex items-center justify-center shadow-glow-sm">
            <BrainCircuit size={20} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-white text-sm leading-tight">AI Viva Examination</p>
            {title && <p className="text-xs text-slate-500 mt-0.5">{title}</p>}
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold text-white">{answered}<span className="text-slate-500 font-normal"> / {totalQ}</span></p>
          <p className="text-xs text-slate-600">answered</p>
        </div>
      </div>

      {/* ── Progress ──────────────────────────────────────────────────────── */}
      <div>
        <div className="flex justify-between text-xs text-slate-600 mb-1.5">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="progress-bar h-2">
          <div className="progress-fill h-2" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {/* ── Last answer feedback ───────────────────────────────────────────── */}
      {lastEval && (
        <div className={`flex items-start gap-3 px-4 py-3.5 rounded-xl border text-sm
          ${lastEval.is_weak
            ? 'bg-amber-500/10 border-amber-500/20'
            : 'bg-green-500/10 border-green-500/20'}`}>
          {lastEval.is_weak
            ? <AlertCircle size={16} className="text-amber-400 mt-0.5 shrink-0" />
            : <CheckCircle2 size={16} className="text-green-400 mt-0.5 shrink-0" />}
          <div className="min-w-0">
            <p className={`font-semibold ${lastEval.is_weak ? 'text-amber-300' : 'text-green-300'}`}>
              Score {lastEval.score?.toFixed(1)}/10
              {lastEval.is_weak ? ' — Follow-up question incoming' : ' — Well answered!'}
            </p>
            <p className={`text-xs mt-1 ${lastEval.is_weak ? 'text-amber-400/80' : 'text-green-400/80'}`}>
              {lastEval.feedback}
            </p>
          </div>
        </div>
      )}

      {/* ── Voice confidence strip ─────────────────────────────────────────── */}
      {lastVoice?.confidence && (
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          {[
            { label: 'Confidence',   value: `${lastVoice.confidence.confidence_score}/100`, ok: lastVoice.confidence.confidence_score >= 50 },
            { label: 'Speech Rate',  value: `${lastVoice.confidence.speech_rate_wpm} WPM`,  ok: lastVoice.confidence.speech_rate_wpm >= 80 },
            { label: 'Filler Words', value: `${lastVoice.confidence.filler_ratio}%`,         ok: lastVoice.confidence.filler_ratio < 15 },
          ].map(({ label, value, ok }) => (
            <div key={label} className={`px-3 py-2 rounded-xl border ${ok ? 'bg-green-500/10 border-green-500/20' : 'bg-amber-500/10 border-amber-500/20'}`}>
              <p className={`font-bold ${ok ? 'text-green-300' : 'text-amber-300'}`}>{value}</p>
              <p className="text-slate-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Integrity alert ────────────────────────────────────────────────── */}
      {cheat?.is_suspicious && (
        <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20">
          <ShieldAlert size={16} className="text-red-400 mt-0.5 shrink-0" />
          <div className="text-xs">
            <p className="text-red-300 font-semibold">Integrity Alert — {cheat.risk_level}</p>
            {cheat.flags?.slice(0, 2).map((f: any, i: number) => (
              <p key={i} className="text-red-400/70 mt-1">• {f.detail}</p>
            ))}
          </div>
        </div>
      )}

      {/* ── Question card ─────────────────────────────────────────────────── */}
      <div className="glass-card space-y-5">

        {/* Question meta */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-slate-600 font-mono">Q{exchange.sequence_number}</span>
            {isFollowUp && (
              <span className="badge bg-amber-500/15 text-amber-400 border border-amber-500/20">
                Follow-up
              </span>
            )}
            <span className={`badge border ${DIFF_STYLE[exchange.difficulty] || 'bg-white/10 text-slate-400 border-white/10'}`}>
              {exchange.difficulty}
            </span>
            <span className={`badge ${TYPE_STYLE[exchange.question_type] || 'bg-white/10 text-slate-400'}`}>
              {exchange.question_type}
            </span>
          </div>
          {exchange.topic && (
            <span className="text-xs bg-white/5 text-slate-500 px-3 py-1 rounded-full border border-white/10">
              {exchange.topic}
            </span>
          )}
        </div>

        {/* Question text */}
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-500/15 flex items-center justify-center shrink-0 mt-0.5">
            <BookOpen size={15} className="text-brand-400" />
          </div>
          <p className="text-slate-100 text-lg leading-relaxed font-medium flex-1">
            {exchange.question}
          </p>
        </div>

        <div className="border-t border-white/10" />

        {/* Voice answer section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Volume2 size={15} className="text-brand-400" />
              <span className="text-sm font-semibold text-slate-200">Speak Your Answer</span>
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingUp size={12} className="text-slate-600" />
              <span className="text-xs text-slate-600">Confidence + integrity tracked</span>
            </div>
          </div>

          {/* Countdown overlay */}
          {countdown > 0 && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-brand-500/10 border border-brand-500/20">
              <div className="w-8 h-8 rounded-full bg-brand-gradient flex items-center justify-center text-white font-bold text-sm shadow-glow-sm">
                {countdown}
              </div>
              <div>
                <p className="text-brand-300 text-sm font-medium">Read the question carefully</p>
                <p className="text-slate-500 text-xs">Recording will auto-start in {countdown} second{countdown !== 1 ? 's' : ''}</p>
              </div>
            </div>
          )}

          {/* Voice Recorder */}
          <VoiceRecorder
            onTranscriptReady={handleVoiceReady}
            onRecordingStart={() => { recordRef.current = Date.now() }}
            disabled={submitting || countdown > 0}
            autoStart={voiceReady && countdown === 0}
            maxSeconds={120}
          />

          {submitting && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-brand-500/10 border border-brand-500/20">
              <Spinner size="sm" />
              <div>
                <p className="text-brand-300 text-sm font-medium">Processing your answer...</p>
                <p className="text-slate-500 text-xs">Transcribing speech → evaluating content → checking integrity</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer hint */}
      <p className="text-center text-xs text-slate-600">
        Your voice is analyzed for confidence, speech rate, and integrity patterns.
        Speak clearly and answer in full sentences.
      </p>
    </div>
  )
}
