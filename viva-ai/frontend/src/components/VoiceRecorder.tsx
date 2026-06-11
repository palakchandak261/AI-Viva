import { useEffect, useCallback } from 'react'
import { Mic, Square, AlertTriangle, CheckCircle2, Loader2, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'

interface Props {
  onTranscriptReady: (blob: Blob, durationSeconds: number) => void
  onRecordingStart?: () => void
  disabled?: boolean
  maxSeconds?: number
  autoStart?: boolean
}

export default function VoiceRecorder({
  onTranscriptReady, onRecordingStart,
  disabled = false, maxSeconds = 120, autoStart = false
}: Props) {
  const { state, duration, waveform, audioBlob, error, startRecording, stopRecording, resetRecorder } = useVoiceRecorder()

  const startWithCallback = useCallback(async () => {
    onRecordingStart?.()
    await startRecording()
  }, [onRecordingStart, startRecording])

  // Auto-stop at limit
  useEffect(() => {
    if (duration >= maxSeconds && state === 'recording') stopRecording()
  }, [duration, maxSeconds, state, stopRecording])

  // Auto-start when parent says go
  useEffect(() => {
    if (autoStart && state === 'idle' && !disabled) startWithCallback()
  }, [autoStart, state, disabled]) // eslint-disable-line

  // Notify parent when blob ready
  useEffect(() => {
    if (audioBlob) onTranscriptReady(audioBlob, duration)
  }, [audioBlob]) // eslint-disable-line

  const isRecording = state === 'recording'
  const isProcessing = state === 'processing'
  const isRequesting = state === 'requesting'
  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
  const pct = Math.min(100, (duration / maxSeconds) * 100)
  const nearLimit = maxSeconds - duration <= 15 && isRecording

  return (
    <div className="space-y-4">
      {/* Waveform */}
      <div className={clsx(
        'relative flex items-center justify-center gap-[3px] h-20 px-6 rounded-2xl transition-all duration-300 overflow-hidden',
        isRecording
          ? 'bg-red-500/10 border-2 border-red-500/40'
          : audioBlob && state === 'idle'
          ? 'bg-green-500/10 border-2 border-green-500/30'
          : 'bg-white/5 border-2 border-white/10'
      )}>
        {waveform.map((val, i) => (
          <div key={i}
            className={clsx('rounded-full transition-all duration-75 min-h-[3px]',
              isRecording ? 'bg-red-400' : audioBlob ? 'bg-green-400' : 'bg-slate-600'
            )}
            style={{ width: '3px', height: `${Math.max(3, val * 0.64)}px` }}
          />
        ))}
        {/* Overlay label when idle */}
        {!isRecording && !isProcessing && !isRequesting && !audioBlob && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-slate-500 text-sm">
              {disabled ? 'Preparing...' : 'Press Record to start speaking'}
            </p>
          </div>
        )}
        {isRequesting && (
          <div className="absolute inset-0 flex items-center justify-center gap-2">
            <Loader2 size={16} className="animate-spin text-brand-400" />
            <p className="text-slate-400 text-sm">Accessing microphone...</p>
          </div>
        )}
      </div>

      {/* Progress ring for time limit */}
      {isRecording && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className={clsx('font-mono font-bold', nearLimit ? 'text-red-400' : 'text-slate-400')}>
              {fmt(duration)}
            </span>
            <span className={clsx('font-mono', nearLimit ? 'text-red-400' : 'text-slate-600')}>
              {fmt(maxSeconds - duration)} left
            </span>
          </div>
          <div className="w-full bg-white/10 rounded-full h-1.5">
            <div
              className={clsx('h-1.5 rounded-full transition-all duration-1000', nearLimit ? 'bg-red-500' : 'bg-brand-500')}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1">
          {!isRecording ? (
            <button onClick={startWithCallback} disabled={disabled || isProcessing || isRequesting}
              className={clsx(
                'flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all duration-200',
                disabled || isProcessing || isRequesting
                  ? 'bg-white/5 text-slate-500 cursor-not-allowed'
                  : 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/25 hover:-translate-y-0.5'
              )}>
              {isProcessing || isRequesting
                ? <><Loader2 size={16} className="animate-spin" /> {isProcessing ? 'Processing...' : 'Starting...'}</>
                : <><Mic size={16} /> {audioBlob ? 'Record Again' : 'Start Recording'}</>
              }
            </button>
          ) : (
            <button onClick={stopRecording}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm bg-slate-700 hover:bg-slate-600 text-white border border-white/10 transition-all duration-200">
              <Square size={16} className="text-red-400" />
              Stop Recording
            </button>
          )}

          {audioBlob && state === 'idle' && (
            <button onClick={resetRecorder}
              className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium bg-white/5 text-slate-400 hover:bg-white/10 hover:text-slate-200 border border-white/10 transition-all duration-200">
              <RefreshCw size={14} />
              Re-record
            </button>
          )}
        </div>
      </div>

      {/* Status messages */}
      {error && (
        <div className="flex items-start gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-300">
          <AlertTriangle size={15} className="shrink-0 mt-0.5" />
          {error.toLowerCase().includes('denied')
            ? 'Microphone blocked. Allow microphone access in your browser settings and reload.'
            : error}
        </div>
      )}
      {audioBlob && state === 'idle' && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-green-500/10 border border-green-500/20 text-sm text-green-300">
          <CheckCircle2 size={15} />
          Recording captured ({fmt(duration)}) — submitting to AI for evaluation...
        </div>
      )}
      {isRecording && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          Recording in progress — speak clearly, answer the question fully
        </div>
      )}
    </div>
  )
}
