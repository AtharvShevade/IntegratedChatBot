import { useCallback, useRef, useState } from 'react'

export function useVoiceRecorder() {
  const [state, setState] = useState('idle')
  const [audioBlob, setAudioBlob] = useState(null)
  const [mimeType, setMimeType] = useState('audio/webm')
  const [error, setError] = useState(null)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  const start = useCallback(async () => {
    setError(null)
    setAudioBlob(null)
    chunksRef.current = []

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setError('Microphone access denied. Please allow microphone permission.')
      return
    }

    // Prefer WAV; fall back to webm/ogg
    const preferredMime =
      ['audio/wav', 'audio/webm', 'audio/ogg'].find((m) =>
        MediaRecorder.isTypeSupported(m),
      ) ?? 'audio/webm'

    setMimeType(preferredMime)

    const mr = new MediaRecorder(stream, { mimeType: preferredMime })
    mediaRecorderRef.current = mr

    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }

    mr.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: preferredMime })
      setAudioBlob(blob)
      stream.getTracks().forEach((t) => t.stop())
      setState('done')
    }

    mr.start(250) // collect data every 250ms
    setState('recording')
  }, [])

  const stop = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  const reset = useCallback(() => {
    stop()
    setAudioBlob(null)
    setState('idle')
    setError(null)
  }, [stop])

  return { state, audioBlob, mimeType, start, stop, reset, error }
}
