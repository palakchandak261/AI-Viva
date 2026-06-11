import clsx from 'clsx'
import { TrendingUp, AlertTriangle, ShieldAlert } from 'lucide-react'

interface ConfidenceData {
  confidence_score: number
  confidence_label: string
  speech_rate_wpm: number
  filler_count: number
  filler_ratio: number
  pause_count: number
  long_pause_count: number
  vocabulary_diversity: number
  answer_length_words: number
  signals: string[]
}

interface CheatData {
  risk_score: number
  risk_level: string
  is_suspicious: boolean
  flags: Array<{ type: string; severity: string; detail: string }>
  summary: string
}

interface Props {
  confidence: ConfidenceData
  cheatDetection: CheatData
}

export default function ConfidenceMeter({ confidence, cheatDetection }: Props) {
  const { confidence_score, confidence_label, speech_rate_wpm, filler_ratio,
    answer_length_words, signals, vocabulary_diversity } = confidence

  const scoreColor = (score: number) =>
    score >= 75 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-600'

  const barColor = (score: number) =>
    score >= 75 ? 'bg-green-500' : score >= 50 ? 'bg-yellow-500' : 'bg-red-500'

  const cheatColor = cheatDetection.is_suspicious ? 'border-red-300 bg-red-50' : 'border-green-200 bg-green-50'

  return (
    <div className="space-y-4 mt-4">
      {/* Confidence score */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
            <TrendingUp size={16} className="text-brand-600" />
            Voice Confidence Analysis
          </div>
          <div className={clsx('text-xl font-bold', scoreColor(confidence_score))}>
            {confidence_score}<span className="text-sm font-normal">/100</span>
          </div>
        </div>

        {/* Confidence bar */}
        <div className="w-full bg-gray-200 rounded-full h-2.5 mb-3">
          <div
            className={clsx('h-2.5 rounded-full transition-all duration-700', barColor(confidence_score))}
            style={{ width: `${confidence_score}%` }}
          />
        </div>

        <p className={clsx('text-sm font-medium mb-3', scoreColor(confidence_score))}>
          {confidence_label}
        </p>

        {/* Metrics grid */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          {[
            { label: 'Speech Rate', value: `${speech_rate_wpm} WPM`, good: speech_rate_wpm >= 100 && speech_rate_wpm <= 200 },
            { label: 'Filler Words', value: `${filler_ratio}%`, good: filler_ratio < 10 },
            { label: 'Word Count', value: `${answer_length_words} words`, good: answer_length_words >= 30 },
            { label: 'Vocabulary', value: `${vocabulary_diversity}% unique`, good: vocabulary_diversity >= 50 },
          ].map(({ label, value, good }) => (
            <div key={label} className={clsx(
              'px-2.5 py-1.5 rounded-lg flex items-center justify-between',
              good ? 'bg-green-50 text-green-800' : 'bg-yellow-50 text-yellow-800'
            )}>
              <span className="text-gray-500">{label}</span>
              <span className="font-medium">{value}</span>
            </div>
          ))}
        </div>

        {/* Signals */}
        {signals.length > 0 && (
          <div className="mt-3 space-y-1">
            {signals.map((s, i) => (
              <p key={i} className="text-xs text-gray-500 flex items-center gap-1">
                <span className="text-gray-400">•</span> {s}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* Cheat detection */}
      <div className={clsx('rounded-xl border p-4', cheatColor)}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <ShieldAlert size={16} className={cheatDetection.is_suspicious ? 'text-red-600' : 'text-green-600'} />
            Integrity Check
          </div>
          <span className={clsx(
            'text-xs font-bold px-2 py-0.5 rounded-full',
            cheatDetection.is_suspicious ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
          )}>
            {cheatDetection.risk_level}
          </span>
        </div>

        <p className={clsx('text-sm', cheatDetection.is_suspicious ? 'text-red-700' : 'text-green-700')}>
          {cheatDetection.summary}
        </p>

        {cheatDetection.flags.length > 0 && (
          <div className="mt-3 space-y-2">
            {cheatDetection.flags.map((flag, i) => (
              <div key={i} className={clsx(
                'flex items-start gap-2 text-xs px-3 py-2 rounded-lg',
                flag.severity === 'high' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
              )}>
                <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                <span>{flag.detail}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
