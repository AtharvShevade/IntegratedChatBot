import { useState, useRef, useCallback } from 'react'
import { transcribeAudio } from '../services/api.js'

/**
 * VoiceInput — Push-to-talk microphone button.
 *
 * Flow:
 *  1. User clicks/taps the mic button  → start recording via MediaRecorder
 *  2. User clicks again (or holds)     → stop recording
 *  3. Recorded audio blob              → POST /speech-to-text (proxied to Sarvam AI)
 *  4. Transcript string                → passed up via onTranscript callback
 */
export default function VoiceInput({ onTranscript, disabled }) {
  const [state, setState] = useState('idle') // 'idle' | 'recording' | 'processing'
  const [error, setError] = useState(null)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  const startRecording = useCallback(async () => {
    setError(null)
    chunksRef.current = []

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      setError('Microphone access denied.')
      return
    }

    // Prefer webm/opus (widely supported); fall back to browser default
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : ''

    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {})
    mediaRecorderRef.current = recorder

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }

    recorder.onstop = async () => {
      // Stop all mic tracks to release the browser mic indicator
      stream.getTracks().forEach((t) => t.stop())

      const blob = new Blob(chunksRef.current, {
        type: recorder.mimeType || 'audio/webm',
      })

      setState('processing')
      try {
        const transcript = await transcribeAudio(blob)
        if (transcript) {
          onTranscript(transcript)
        } else {
          setError('No speech detected. Please try again.')
        }
      } catch (err) {
        setError(err.message || 'Transcription failed.')
      } finally {
        setState('idle')
      }
    }

    recorder.start()
    setState('recording')
  }, [onTranscript])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  const handleClick = () => {
    if (state === 'idle') startRecording()
    else if (state === 'recording') stopRecording()
  }

  const label =
    state === 'recording'
      ? 'Stop recording'
      : state === 'processing'
      ? 'Transcribing…'
      : 'Start voice input'

  return (
    <div className="voice-input-wrapper">
      <button
        type="button"
        className={`mic-btn mic-btn--${state}`}
        onClick={handleClick}
        disabled={disabled || state === 'processing'}
        aria-label={label}
        title={label}
      >
        {state === 'processing' ? <SpinnerIcon /> : <MicIcon active={state === 'recording'} />}
      </button>

      {/* Inline error shown just above the button */}
      {error && <span className="mic-error">{error}</span>}
    </div>
  )
}

function MicIcon({ active }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="11" rx="3" fill={active ? 'currentColor' : 'none'} />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  )
}

function SpinnerIcon() {
  return (
    <svg className="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  )
}
