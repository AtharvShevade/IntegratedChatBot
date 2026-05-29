import { useState, useRef, useEffect } from 'react'
import ChatWindow from './components/ChatWindow.jsx'
import VoiceInput from './components/VoiceInput.jsx'
import { sendMessage, sendGuidedMessage, compareInstances, findReturnTables, computeVariance } from './services/api.js'

// Read loginId / uid / aspSession injected by the .NET iframe URL.
// On first load with URL params, save them to sessionStorage so identity
// survives a page refresh (the .NET params are only in the URL on first load).
const _params     = new URLSearchParams(window.location.search)

function _readParam(urlKey, sessionKey) {
  const fromUrl = _params.get(urlKey) || ''
  if (fromUrl) {
    sessionStorage.setItem(sessionKey, fromUrl)
    return fromUrl
  }
  return sessionStorage.getItem(sessionKey) || ''
}

const _loginId    = _readParam('loginId',    'chat_loginId')
const _uid        = _readParam('uid',         'chat_uid')
const _roleId     = _readParam('roleId',      'chat_roleId') || _readParam('rid', 'chat_rid') || ''
const _aspSession = _params.get('aspSession') || ''  // never persisted — cookie-like, must be fresh

// ── Persistent storage key (isolated per uid) ─────────────────────────────
const STORAGE_KEY = `chat_history_${_uid}`

// Extract the last n user/assistant messages for conversation context.
// Skips system roles (welcome, error, action_menu, etc.).
function _getRecentHistory(messages, n = 7) {
  return messages
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .map((m) => ({ role: m.role, text: m.text || '' }))
    .filter((m) => m.text)
    .slice(-n)
}

// Load saved messages from localStorage; fall back to the welcome card.
function _loadHistory() {
  if (!_uid) return [{ role: 'welcome' }]
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length > 0) return parsed
    }
  } catch {
    // Corrupted data — start fresh
  }
  return [{ role: 'welcome' }]
}

export default function App() {
  const [messages, setMessages]       = useState(_loadHistory)
  const [inputText, setInputText]     = useState('')
  const [isLoading, setIsLoading]     = useState(false)
  const [isGuidedFlow, setIsGuidedFlow] = useState(false)
  const inputRef  = useRef(null)
  const sessionId = useRef(_uid || crypto.randomUUID())

  // ── Variance guided flow state ────────────────────────────────────────────
  // Tracks which step the user is on so typed input is routed correctly.
  // Steps: null → 'await_return_name' → 'await_table' → 'await_date' → 'await_periods' → done
  const [varianceStep, setVarianceStep]   = useState(null)
  const [varianceInfo, setVarianceInfo]   = useState(null)  // result of /variance/find
  const [varianceTable, setVarianceTable] = useState(null)  // chosen table name

  // ── Persist messages to localStorage on every change ─────────────────────
  useEffect(() => {
    if (!_uid) return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
    } catch {
      // Storage quota exceeded or private-browsing restriction — ignore silently
    }
  }, [messages])

  // ── Clear chat ────────────────────────────────────────────────────────────
  const handleClearChat = () => {
    try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
    setMessages([{ role: 'welcome' }])
    setIsGuidedFlow(false)
  }

  // Result types that represent a fully completed workflow.
  // After these, the action menu re-appears so the user can start another task.
  const _TERMINAL_TYPES = new Set([
    'final',           // report status check done
    'variance_table',  // comparative analysis done
    'gen_success',     // report generation done
    'schedule_parsed', // scheduling confirmed
    'sql_result',      // database query done
    'db_result',       // SQL agent query done
  ])

  // ── Helper: push an assistant result into the message list ───────────────
  const _pushResult = (result) => {
    const isTerminal    = _TERMINAL_TYPES.has(result.result_type)
    const isStillGuided =
      result.result_type === 'guided_menu' || result.result_type === 'guided_input'
    setIsGuidedFlow(isTerminal ? false : isStillGuided)

    // Append more_info_hint to the displayed text when the backend signals
    // that the query needs more detail (short query, no results, etc.)
    const moreInfoHint = result.needs_more_info && result.more_info_hint
      ? result.more_info_hint : null
    const displayText = moreInfoHint
      ? `${result.response_text}\n\n${moreInfoHint}` : result.response_text

    // Only pass sqlData when there are actual rows — triggers the table UI.
    // For no-results / error / too-short cases the text bubble is used instead.
    const sqlData = result.result_type === 'db_result' && result.db_rows?.length > 0
      ? {
          sql:             result.db_sql      || '',
          is_valid:        !result.db_error,
          db_error:        result.db_error    || null,
          columns:         result.db_columns  || [],
          rows:            result.db_rows     || [],
          matched_tables:  [],
          matched_columns: [],
        }
      : null

    const resultMsg = {
      role:          'assistant',
      text:          displayText,
      options:       result.options || [],
      resultType:    result.result_type || '',
      sqlData,
      varianceData:  result.variance_data || [],
      labelA:        result.variance_label_a || '',
      labelB:        result.variance_label_b || '',
      llmSummary:    result.llm_summary || '',
      instancesData: result.instances_data || [],
      downloadUrl:   result.download_url   || '',
      downloadLabel: result.download_label || '',
      statusNote:    result.status_note    || '',
    }
    setMessages((prev) => [...prev, resultMsg])
    if (isTerminal) {
      setTimeout(() => {
        setMessages((prev) => [...prev, { role: 'feedback_prompt' }])
      }, 1000)
    }
  }

  // ── Free-text chat ────────────────────────────────────────────────────────
  const submitChatMessage = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    // Capture history BEFORE appending the current user message
    const recentHistory = _getRecentHistory(messages)

    setMessages((prev) => [...prev, { role: 'user', text: trimmed }])
    setIsLoading(true)

    try {
      const result = await sendMessage(
        trimmed,
        sessionId.current,
        _aspSession || null,
        _loginId || null,
        _uid || null,
        _roleId || null,
        recentHistory,
      )
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
      const result = await sendGuidedMessage(
        trimmed,
        sessionId.current,
        _aspSession || null,
        _loginId || null,
        _uid || null,
        _roleId || null,
      )
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

  // ── Variance: map frequency code → date hint shown to the user ──────────
  const _varianceDateHint = (freq) => {
    const f = (freq || '').toUpperCase()
    const y = new Date().getFullYear()
    if (['A', 'ANNUAL', 'Y', 'FY'].includes(f))
      return { example: `31-MAR-${y}`, hint: 'Financial year end — must be 31-Mar.' }
    if (['B', 'CY'].includes(f))
      return { example: `31-DEC-${y}`, hint: 'Calendar year end — must be 31-Dec.' }
    if (['Q', 'QUARTERLY'].includes(f))
      return { example: `31-MAR-${y}`, hint: 'Quarter end — 31-Mar / 30-Jun / 30-Sep / 31-Dec.' }
    if (['H', 'HALFYEARLY', 'HY', 'FH'].includes(f))
      return { example: `31-MAR-${y}`, hint: 'Financial half-year — 31-Mar or 30-Sep.' }
    if (['C', 'CH'].includes(f))
      return { example: `30-JUN-${y}`, hint: 'Calendar half-year — 30-Jun or 31-Dec.' }
    if (['W', 'WEEKLY'].includes(f))
      return { example: 'any Friday', hint: 'Weekly — must be a Friday.' }
    if (['F', 'FORTNIGHTLY', 'HM'].includes(f))
      return { example: `15-MAR-${y}`, hint: 'Fortnightly — 15th or last day of month.' }
    if (['D', 'DAILY', 'G'].includes(f))
      return { example: `26-MAY-${y}`, hint: 'Daily — any valid past date.' }
    // Default: monthly
    return { example: `31-MAR-${y}`, hint: 'Monthly — last day of the month.' }
  }

  // ── Variance: step 1 — user clicks 'Data variance' action button ─────────
  const handleVarianceStart = () => {
    setVarianceStep('await_return_name')
    setVarianceInfo(null)
    setVarianceTable(null)
    setIsGuidedFlow(true)
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: 'Data variance' },
      {
        role: 'assistant',
        text: '📈 Data Variance\nEnter the return or report name to look up (e.g. CIMS_RAQ):',
        resultType: 'guided_input',
        options: [],
      },
    ])
  }

  // ── Variance: step 2 — /variance/find then show table picker ─────────────
  const handleVarianceFindReturn = async (returnName) => {
    setMessages((prev) => [...prev, { role: 'user', text: returnName }])
    setIsLoading(true)
    try {
      const info = await findReturnTables(returnName)
      setVarianceInfo(info)
      setVarianceStep('await_table')
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          resultType: 'variance_find_result',
          text: '',
          varianceFindResult: info,
        },
      ])
    } catch (err) {
      setVarianceStep(null)
      setIsGuidedFlow(false)
      setMessages((prev) => [...prev, { role: 'error', text: err.message }])
    } finally {
      setIsLoading(false)
    }
  }

  // ── Variance: step 3 — user picks a table, ask for date ──────────────────
  const handleVarianceTableSelect = (info, tableName) => {
    setVarianceTable(tableName)
    setVarianceInfo(info)
    setVarianceStep('await_date')
    const { example, hint } = _varianceDateHint(info?.report_freq)
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: tableName },
      {
        role: 'assistant',
        text: `🧭 Guided\nTable selected: **${tableName}**\nEnter the reporting date (DD-MMM-YYYY, e.g. ${example}):\n_${hint}_`,
        resultType: 'guided_input',
        options: [],
      },
    ])
  }

  // ── Variance: step 4 — date entered, ask number of periods ───────────────
  const handleVarianceDateEntered = (dateStr) => {
    setVarianceStep({ step: 'await_periods', date: dateStr })
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: dateStr },
      {
        role: 'assistant',
        text: 'How many previous periods to compare? (e.g. 1, 2, 3):',
        resultType: 'guided_input',
        options: ['1', '2', '3'],
      },
    ])
  }

  // ── Variance: step 5 — call /variance/compute and show result ─────────────
  const handleVarianceCompute = async (periodsStr) => {
    const date    = varianceStep?.date
    const periods = parseInt(periodsStr, 10) || 1
    if (!varianceInfo || !varianceTable || !date) return
    setMessages((prev) => [...prev, { role: 'user', text: String(periods) }])
    setIsLoading(true)
    try {
      const result = await computeVariance({
        return_id:          varianceInfo.return_id,
        table_mapping_path: varianceInfo.table_mapping_path,
        table_name:         varianceTable,
        reporting_date:     date,
        reporting_period:   periods,
      })
      setVarianceStep(null)
      setIsGuidedFlow(false)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          resultType: 'data_variance_result',
          text: '',
          dataVarianceResult: result,
        },
      ])
      setTimeout(() => {
        setMessages((prev) => [...prev, { role: 'feedback_prompt' }])
      }, 800)
    } catch (err) {
      setVarianceStep(null)
      setIsGuidedFlow(false)
      setMessages((prev) => [...prev, { role: 'error', text: err.message }])
    } finally {
      setIsLoading(false)
    }
  }

  // ── Variance: after result — Explain / Visualize buttons ─────────────────
  const handleVarianceAction = (action, result) => {
    if (action === 'explain') {
      setMessages((prev) => [
        ...prev,
        { role: 'user', text: 'Explain This Variance' },
        {
          role: 'assistant',
          text: `📊 Variance Summary for ${result.table_name} (${result.reporting_date} vs ${(result.comparison_periods || []).join(', ')}):\n` +
            (result.rows || []).slice(0, 5).map((r) => {
              const cols = result.columns || []
              const changes = cols.map((col) => {
                const p1 = r.previous?.previous_1?.[col]
                if (!p1) return null
                const vs = p1.variance_summary
                return vs ? `${col}: ${vs.text}` : null
              }).filter(Boolean)
              return `• ${r.identifier}: ${changes.join(', ') || 'no numeric change'}`
            }).join('\n') +
            (result.rows?.length > 5 ? `\n…and ${result.rows.length - 5} more rows.` : ''),
          resultType: 'final',
        },
      ])
    } else if (action === 'visualize') {
      setMessages((prev) => [
        ...prev,
        { role: 'user', text: 'Visualize' },
        {
          role: 'assistant',
          text: 'Visualization is not yet available in this interface. You can export the data and use Excel or a BI tool to create charts.',
          resultType: 'final',
        },
      ])
    }
  }

  // ── Start guided flow via welcome card action button ────────────────────
  const handleGuidedAction = async (action) => {
    if (isLoading) return
    // intercept 'Data variance' — use local flow, not backend guided
    if (action === 'Data variance') {
      handleVarianceStart()
      return
    }
    setIsGuidedFlow(true)
    setMessages((prev) => [...prev, { role: 'user', text: action }])
    setIsLoading(true)
    try {
      const result = await sendGuidedMessage(
        action,
        sessionId.current,
        _aspSession || null,
        _loginId || null,
        _uid || null,
        _roleId || null,
      )
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

  // ── Feedback after completed action ──────────────────────────────────────
  const handleFeedback = (response) => {
    if (response === 'yes') {
      setMessages((prev) => [...prev, { role: 'feedback_positive' }])
    } else {
      setMessages((prev) => [...prev, { role: 'feedback_negative' }])
    }
    setTimeout(() => {
      setMessages((prev) => [...prev, { role: 'action_menu' }])
    }, 800)
  }

  // ── Chip / option click ───────────────────────────────────────────────────
  const handleSuggestion = (text) => {    if (varianceStep === 'await_return_name') {
      handleVarianceFindReturn(text); return
    }
    if (varianceStep === 'await_table') {
      return // handled by VarianceFindBlock directly
    }
    if (varianceStep === 'await_date') {
      handleVarianceDateEntered(text); return
    }
    if (varianceStep?.step === 'await_periods') {
      handleVarianceCompute(text); return
    }    if (isGuidedFlow) {
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
    // route through variance step handlers if in variance guided flow
    if (varianceStep === 'await_return_name') { await handleVarianceFindReturn(text); return }
    if (varianceStep === 'await_date')        { handleVarianceDateEntered(text); return }
    if (varianceStep?.step === 'await_periods') { await handleVarianceCompute(text); return }
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
      <main className="chat-area">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSuggestion={handleSuggestion}
          onGuidedAction={handleGuidedAction}
          onCompare={handleCompareInstances}
          onFeedback={handleFeedback}
          onVarianceTableSelect={handleVarianceTableSelect}
          onVarianceCompute={handleVarianceAction}
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
            type="button"
            className="clear-chat-btn"
            onClick={handleClearChat}
            title="Clear chat history"
            aria-label="Clear chat history"
          >
            <TrashIcon />
          </button>
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

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  )
}
 