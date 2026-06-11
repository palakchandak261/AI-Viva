/**
 * useVoiceRecorder
 * Handles microphone recording, live waveform data, and audio blob output.
 */
import { useState, useRef, useCallback, useEffect } from 'react'

export type RecorderState = 'idle' | 'requesting' | 'recording' | 'processing' | 'error'

export interface VoiceRecorderResult {
  state: RecorderState
  duration: number          // seconds recording has been running
  waveform: number[]        // 32 amplitude values for live visualizer
  audioBlob: Blob | null
  error: string | null
  startRecording: () => Promise<void>
  stopRecording: () => void
  resetRecorder: () => void
}

export function useVoiceRecorder(): VoiceRecorderResult {
  const [state, setState] = useState<RecorderState>('idle')
  const [duration, setDuration] = useState(0)
  const [waveform, setWaveform] = useState<number[]>(new Array(32).fill(0))
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [error, setError] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animFrameRef = useRef<number | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const stopAll = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
    if (animFrameRef.current) { cancelAnimationFrame(animFrameRef.current); animFrameRef.current = null }
    if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null }
  }, [])

  const startRecording = useCallback(async () => {
    setError(null)
    setAudioBlob(null)
    setDuration(0)
    setState('requesting')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 }
      })
      streamRef.current = stream

      // Set up analyser for waveform
      const ctx = new AudioContext()
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 64
      source.connect(analyser)
      analyserRef.current = analyser

      // Live waveform animation
      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      const drawWave = () => {
        analyser.getByteFrequencyData(dataArray)
        const bars = Array.from({ length: 32 }, (_, i) =>
          Math.round((dataArray[i] / 255) * 100)
        )
        setWaveform(bars)
        animFrameRef.current = requestAnimationFrame(drawWave)
      }
      drawWave()

      // MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'

      const recorder = new MediaRecorder(stream, { mimeType })
      chunksRef.current = []
      recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType })
        setAudioBlob(blob)
        setState('idle')
        setWaveform(new Array(32).fill(0))
      }

      recorder.start(100) // collect in 100ms chunks
      mediaRecorderRef.current = recorder
      setState('recording')

      // Duration counter
      timerRef.current = setInterval(() => setDuration(d => d + 1), 1000)

    } catch (err: any) {
      setError(err.message || 'Microphone access denied')
      setState('error')
      stopAll()
    }
  }, [stopAll])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      setState('processing')
      mediaRecorderRef.current.stop()
    }
    stopAll()
  }, [stopAll])

  const resetRecorder = useCallback(() => {
    stopAll()
    setAudioBlob(null)
    setError(null)
    setDuration(0)
    setWaveform(new Array(32).fill(0))
    setState('idle')
  }, [stopAll])

  useEffect(() => () => stopAll(), [stopAll])

  return { state, duration, waveform, audioBlob, error, startRecording, stopRecording, resetRecorder }
}
