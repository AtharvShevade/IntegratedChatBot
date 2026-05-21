import { useState, useRef } from 'react'
import ChatWindow from './components/ChatWindow.jsx'
import VoiceInput from './components/VoiceInput.jsx'
import { sendMessage, sendGuidedMessage, compareInstances } from './services/api.js'

// Read loginId / uid / aspSession injected by the .NET iframe URL
const _params     = new URLSearchParams(window.location.search)
const _loginId    = _params.get('loginId')    || ''
const _uid        = _params.get('uid')        || ''
const _aspSession = _params.get('aspSession') || ''

export default function App() {
  const [messages, setMessages]       = useState([{ role: 'welcome' }])
  const [inputText, setInputText]     = useState('')
  const [isLoading, setIsLoading]     = useState(false)
  const [isGuidedFlow, setIsGuidedFlow] = useState(false)
  const inputRef  = useRef(null)
  const sessionId = useRef(_uid || crypto.randomUUID())

  // Result types that represent a fully completed workflow — show action menu after these.
  const _TERMINAL_TYPES = new Set([
    'final',          // report status check done
    'variance_table', // comparative analysis done
    'gen_success',    // report generation done
    'schedule_parsed',// scheduling confirmed
    'sql_result',     // database query done
  ])

  // ── Helper: push an assistant result into the message list ───────────────
  const _pushResult = (result) => {
    const isTerminal    = _TERMINAL_TYPES.has(result.result_type)
    const isStillGuided =
      result.result_type === 'guided_menu' || result.result_type === 'guided_input'
    setIsGuidedFlow(isTerminal ? false : isStillGuided)

    const incoming = [
      {
        role:          'assistant',
        text:          result.response_text,
        options:       result.options || [],
        resultType:    result.result_type || '',
        varianceData:  result.variance_data || [],
        labelA:        result.variance_label_a || '',
        labelB:        result.variance_label_b || '',
        llmSummary:    result.llm_summary || '',
        instancesData: result.instances_data || [],
      },
    ]
    if (isTerminal) {
      incoming.push({ role: 'action_menu' })
    }
    setMessages((prev) => [...prev, ...incoming])
  }

  // ── Free-text chat ────────────────────────────────────────────────────────
  const submitChatMessage = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    setMessages((prev) => [...prev, { role: 'user', text: trimmed }])
    setIsLoading(true)

    try {
      const result = await sendMessage(trimmed, sessionId.current, _aspSession || null, _loginId || null)
      _pushResult(result)
    } catch (err) {
      setIsGuidedFlow(false)
      setMessages((prev) => [
        ...prev,
        { role: 'error', text: err.message || 'Something went wrong. Please try again.' },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  // ── Guided workflow step ──────────────────────────────────────────────────
  const submitGuidedStep = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    setMessages((prev) => [...prev, { role: 'user', text: trimmed }])
    setIsLoading(true)

    try {
      const result = await sendGuidedMessage(trimmed, sessionId.current, _aspSession || null, _loginId || null)
      _pushResult(result)
    } catch (err) {
      setIsGuidedFlow(false)
      setMessages((prev) => [
        ...prev,
        { role: 'error', text: err.message || 'Something went wrong. Please try again.' },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  // ── Start guided flow via welcome card action button ────────────────────
  const handleGuidedAction = async (action) => {
    if (isLoading) return
    setIsGuidedFlow(true)
    setMessages((prev) => [...prev, { role: 'user', text: action }])
    setIsLoading(true)
    try {
      const result = await sendGuidedMessage(action, sessionId.current, _aspSession || null, _loginId || null)
      _pushResult(result)
    } catch (err) {
      setIsGuidedFlow(false)
      setMessages((prev) => [...prev, { role: 'error', text: err.message }])
    } finally {
      setIsLoading(false)
    }
  }

  // ── Compare Instances button ──────────────────────────────────────────────
  const handleCompareInstances = async (idxA, idxB) => {
    if (isLoading) return
    setMessages((prev) => [...prev, { role: 'user', text: 'Compare Instances' }])
    setIsLoading(true)
    try {
      const result = await compareInstances(sessionId.current, idxA, idxB)
      _pushResult(result)
    } catch (err) {
      setIsGuidedFlow(false)
      setMessages((prev) => [
        ...prev,
        { role: 'error', text: err.message || 'Comparison failed. Please try again.' },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  // ── Chip / option click ───────────────────────────────────────────────────
  const handleSuggestion = (text) => {
    if (isGuidedFlow) {
      submitGuidedStep(text)
    } else {
      submitChatMessage(text)
    }
  }

  const handleTranscript = (transcript) => {
    setInputText(transcript)
    inputRef.current?.focus()
  }

  const handleSubmit = async (e) => {
    e?.preventDefault()
    const text = inputText.trim()
    if (!text || isLoading) return
    setInputText('')
    if (isGuidedFlow) {
      await submitGuidedStep(text)
    } else {
      await submitChatMessage(text)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const placeholder = isGuidedFlow
    ? 'Type your answer…'
    : 'Ask about a report… or press the mic'

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="header-logo">💬</span>
        <h1>AI Report Assistant</h1>
        {_loginId && <span className="header-badge">{_loginId}</span>}
      </header>

      <main className="chat-area">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSuggestion={handleSuggestion}
          onGuidedAction={handleGuidedAction}
          onCompare={handleCompareInstances}
        />
      </main>

      <footer className="input-bar">
        {isGuidedFlow && (
          <div className="guided-mode-indicator">🧭 Guided mode — answer the question above</div>
        )}
        <form className="input-form" onSubmit={handleSubmit}>
          <VoiceInput onTranscript={handleTranscript} disabled={isLoading} />
          <textarea
            ref={inputRef}
            className="text-input"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={!inputText.trim() || isLoading}
            aria-label="Send message"
          >
            <SendIcon />
          </button>
        </form>
      </footer>
    </div>
  )
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  )
}
