import { useState, useRef, useCallback, useEffect } from 'react'
import { transcribeAudio, stopRequest } from '../services/api.js'
import { useT } from '../i18n.js'

/**
 * VoiceInput — Push-to-talk microphone button.
 *
 * Flow:
 *  1. User clicks/taps the mic button  → start recording via MediaRecorder
 *  2. User clicks again (or holds)     → stop recording
 *  3. Recorded audio blob              → POST /speech-to-text (remote Whisper)
 *  4. Transcript string                → passed up via onTranscript callback
 *
 * Transcription is CANCELLABLE. It can take several seconds, so the button
 * stays live and becomes a stop control -- clicking aborts the request AND
 * tells the backend to cancel the work (POST /stop), so a cancelled
 * transcription does not keep occupying the STT service, which transcribes
 * one clip at a time.
 *
 * The transcript is NOT auto-sent. App.jsx puts it in the chat input so the
 * user can correct a misheard report name before pressing Send -- and so STT
 * latency stays outside the chat latency budget.
 */

// Hard cap on one recording. Mirrors STT_MAX_SECONDS on the backend.
// Without it a forgotten open mic becomes an unbounded upload and minutes of
// serialized CPU on the STT host, which transcribes one clip at a time.
const MAX_SECONDS = 60
// When the countdown becomes visible.
const WARN_AT = 10
export default function VoiceInput({ onTranscript, onStateChange, disabled }) {
  const t = useT()
  const [state, setState] = useState('idle') // 'idle' | 'recording' | 'processing'
  const [error, setError] = useState(null)
  const [remaining, setRemaining] = useState(null)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const abortRef = useRef(null)
  const requestIdRef = useRef(null)
  const langRef = useRef(t.lang)

  // The recorder's onstop closure is created once per recording, so it would
  // otherwise capture whichever language was selected when recording STARTED.
  // A ref keeps it current if the user switches language mid-recording.
  useEffect(() => { langRef.current = t.lang }, [t.lang])

  // Let the composer react to the mic: the textarea says "Speak now" while
  // recording, which is the only on-screen cue in the place the user is
  // actually looking -- the button is small and sits at the edge.
  useEffect(() => { onStateChange?.(state) }, [state, onStateChange])

  // Never leave a timer running if the component unmounts mid-recording.
  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current)
    // Unmounting mid-transcription must not leave the request running.
    abortRef.current?.abort()
  }, [])

  const startRecording = useCallback(async () => {
    setError(null)
    chunksRef.current = []

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      setError(t('voice.micRequired'))
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
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
      setRemaining(null)
      // Stop all mic tracks to release the browser mic indicator
      stream.getTracks().forEach((t) => t.stop())

      const blob = new Blob(chunksRef.current, {
        type: recorder.mimeType || 'audio/webm',
      })

      setState('processing')
      const controller = new AbortController()
      abortRef.current = controller
      // Minted client-side, exactly as App.jsx does for /chat, so /stop can
      // cancel the matching asyncio task on the backend.
      const requestId = crypto.randomUUID()
      requestIdRef.current = requestId
      try {
        const transcript = await transcribeAudio(blob, {
          lang: langRef.current, signal: controller.signal, requestId,
        })
        if (transcript) {
          onTranscript(transcript)
        } else {
          setError(t('voice.notHeard'))
        }
      } catch (err) {
        // A user-initiated abort is not an error -- say nothing and go
        // quietly back to idle, the way Stop Generation does for /chat.
        if (err.name !== 'AbortError') {
          setError(err.message || t('voice.transcribeFailed'))
        }
      } finally {
        abortRef.current = null
        requestIdRef.current = null
        setState('idle')
      }
    }

    recorder.start()
    setState('recording')

    // Auto-stop at MAX_SECONDS. Counts down rather than cutting off silently,
    // so the user is never surprised by a truncated recording.
    let left = MAX_SECONDS
    setRemaining(null)
    timerRef.current = setInterval(() => {
      left -= 1
      setRemaining(left <= WARN_AT ? left : null)
      if (left <= 0) stopRecording()
    }, 1000)
  }, [onTranscript])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  const cancelTranscription = useCallback(() => {
    // Abort the fetch so the UI stops waiting immediately...
    abortRef.current?.abort()
    // ...and tell the backend to drop the work. Without this the STT
    // service keeps transcribing a clip nobody is waiting for, and it
    // handles one at a time -- so an abandoned request delays the next
    // user. Best-effort: stopRequest never throws.
    if (requestIdRef.current) stopRequest(requestIdRef.current)
  }, [])

  const handleClick = () => {
    if (state === 'idle') startRecording()
    else if (state === 'recording') stopRecording()
    else if (state === 'processing') cancelTranscription()
  }

  // These three keys already existed in all four languages and were unused;
  // the button previously hardcoded English here, which showed through in
  // FR/AR/HI as the tooltip and the accessible name.
  const label =
    state === 'recording'
      ? t('voice.stop')
      : state === 'processing'
      // Name the ACTION, not the state: the button now cancels, and the
      // tooltip/accessible name must say so or it reads as a dead spinner.
      ? t('voice.stopTranscribing')
      : t('voice.start')

  return (
    <div className="voice-input-wrapper">
      <button
        type="button"
        className={`mic-btn mic-btn--${state}`}
        onClick={handleClick}
        // NOT disabled while processing -- that is exactly when the user
        // needs to be able to cancel.
        disabled={disabled}
        aria-label={label}
        title={label}
      >
        {state === 'processing'
          ? <StopSpinnerIcon />
          : <MicIcon active={state === 'recording'} />}
      </button>

      {remaining !== null && state === 'recording' && (
        <span className="mic-countdown" aria-live="polite">{remaining}s</span>
      )}

      {/* Transcription currently takes several seconds. A spinner alone reads
          as "stuck", so say what is happening in words too -- and announce it,
          since a screen-reader user cannot see the button turn orange. */}
      {state === 'processing' && (
        <span className="mic-processing" role="status" aria-live="polite">
          {t('voice.transcribing')}
        </span>
      )}

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

// Rotating ring (still working) around a static square (click to stop).
// Only the ring spins -- a rotating stop square would read as decoration
// rather than a button.
function StopSpinnerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <g className="spin" style={{ transformOrigin: '12px 12px' }}>
        <circle cx="12" cy="12" r="10" strokeOpacity="0.3" />
        <path d="M12 2a10 10 0 0 1 10 10" />
      </g>
      <rect x="9" y="9" width="6" height="6" rx="1" fill="currentColor" stroke="none" />
    </svg>
  )
}
