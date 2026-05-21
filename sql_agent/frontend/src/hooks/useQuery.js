import { useState } from 'react'
import { runTextQuery, runVoiceQuery } from '../services/api'

export function useQuery() {
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const submitText = async (query, dialect = 'Oracle') => {
    setStatus('loading')
    setError(null)
    setResult(null)
    try {
      const data = await runTextQuery(query, dialect)
      setResult(data)
      setStatus('success')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setStatus('error')
    }
  }

  const submitVoice = async (blob, filename, dialect = 'Oracle') => {
    setStatus('loading')
    setError(null)
    setResult(null)
    try {
      const data = await runVoiceQuery(blob, filename, dialect)
      setResult(data)
      setStatus('success')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setStatus('error')
    }
  }

  const reset = () => {
    setStatus('idle')
    setResult(null)
    setError(null)
  }

  return { status, result, error, submitText, submitVoice, reset }
}
