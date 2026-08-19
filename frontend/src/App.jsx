import { useState, useRef, useEffect } from 'react'
import ChatWindow from './components/ChatWindow.jsx'
import { sendMessage, sendGuidedMessage, compareInstances, explainErrorCategory, stopRequest, getAllowedActions, sendFeedback } from './services/api.js'
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

// APP_VERSION=6.0 only — tenant identity + JWT, read as plain URL params for
// manual/dev testing in THIS standalone test frontend. Note: the real 6.0
// production embed (WebiDEALReact's ChatbotIframe.jsx) does NOT pass the jwt
// via URL — it delivers it through a CHATBOT_READY/CHATBOT_AUTH postMessage
// handshake after the iframe loads. If this frontend is ever embedded the
// same way, replace the `jwt` URL-param read below with that handshake.
const _tenantId   = _readParam('tenant_id',  'chat_tenant_id')
const _domain     = _readParam('domain',     'chat_domain')
const _jwt        = _params.get('jwt') || ''  // never persisted — short-lived, must be fresh

// ── Theme (5.5 vs 6.0) ────────────────────────────────────────────────────
// Same version signal as the backend's APP_VERSION: 6.0's embed always sends
// tenant_id, 5.5's never does. One shared build serves both themes — the
// unused theme's CSS chunk is never fetched, so there's no FOUC/collision
// risk between the two stylesheets.
const _isV6 = Boolean(_tenantId)
if (_isV6) {
  import('./App.6.0.css')
} else {
  import('./App.5.5.css')
}

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
      if (Array.isArray(parsed) && parsed.length > 0) {
        // Restored history is READ-ONLY as far as the backend is concerned:
        // re-rendering an old message must never kick off new work. Variance
        // messages are saved with llmSummary:"" whenever the inline 8s
        // attempt failed, and without this flag the AI-summary effect saw
        // that empty value on every page load and re-generated a summary for
        // every past comparison — explanations appearing on their own after
        // a backend restart, with no user action at all.
        return parsed.map((m) => (
          m && m.resultType === 'variance_table' ? { ...m, noAutoSummary: true } : m
        ))
      }
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
  const inputRef       = useRef(null)
  const sessionId      = useRef(_uid || crypto.randomUUID())
  const pollIntervalRef = useRef(null)
  // Set when a variance table is pushed while its AI summary is still being
  // generated; flushed by handleSummaryLoaded once the summary settles (or
  // the user stops it), so "Was this helpful?" and the next-action menu never
  // land on top of an analysis that is still being written.
  const pendingFollowUpRef = useRef(null)
  // Tracks the in-flight request so the Stop button can abort it client-side
  // and tell the backend to cancel the matching asyncio task.
  const activeRequestRef = useRef(null)

  // ── APP_VERSION=6.0 JWT — real production source is a postMessage
  // handshake with the embedding parent (WebiDEALReact's ChatbotIframe.jsx),
  // NOT a URL param. Starts from the `_jwt` URL-param fallback (manual/dev
  // testing convenience) and gets overwritten the moment a real
  // CHATBOT_AUTH message arrives. A ref (not state) because it's read
  // imperatively at request time, not rendered.
  const jwtRef = useRef(_jwt)
  useEffect(() => {
    if (window.parent === window) return  // not embedded in an iframe — nothing to shake hands with

    function handleAuthMessage(event) {
      if (!event.data || event.data.type !== 'CHATBOT_AUTH') return
      if (typeof event.data.jwt === 'string' && event.data.jwt) {
        jwtRef.current = event.data.jwt
      }
    }
    window.addEventListener('message', handleAuthMessage)
    // Announce readiness so the parent knows to send CHATBOT_AUTH. Target
    // origin "*" here is safe — this message carries no secret, only a
    // ready signal; the parent itself decides which origin to reply to.
    window.parent.postMessage({ type: 'CHATBOT_READY' }, '*')

    return () => window.removeEventListener('message', handleAuthMessage)
  }, [])

  // ── Role-permission-filtered action list (which of the 5 guided actions
  // this user may see/perform — e.g. a Checker never sees Generate/Schedule).
  // Fetched once identity is known so even the very first WelcomeCard render
  // is correctly filtered (not just the in-conversation guided menu, which
  // is filtered server-side on every /guided call regardless of this).
  // Defaults to the full list so nothing is hidden if the fetch hasn't
  // resolved yet or fails — the backend still enforces the real permission
  // on every actual action, so this is a display-only convenience.
  const [allowedActions, setAllowedActions] = useState(null)
  useEffect(() => {
    if (!_loginId) return  // no identity at all — nothing to resolve

    let cancelled = false
    ;(async () => {
      try {
        const actions = await getAllowedActions(_loginId || null, {
          tenantId: _tenantId || null,
          domain: _domain || null,
        })
        if (!cancelled && actions.length > 0) {
          setAllowedActions(actions)
        }
      } catch {
        // Best-effort — keep showing the unfiltered default list on failure;
        // backend enforcement is unaffected either way.
      }
    })()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
    'db_qa_result',    // XML App DB Q&A done
  ])

  // ── Helper: push an assistant result into the message list ───────────────
// *extra* merges additional fields onto the pushed message — used by
// handleExplainCategory to carry batching context (which category/file/
// form/report this explain-result batch belongs to) so an "Explain Next
// Errors" button rendered on this message can re-request the next batch
// without the backend needing to echo those identifiers back.
const _pushResult = (result, extra = {}) => {
  const isTerminal = _TERMINAL_TYPES.has(result.result_type)
  const jobId = result.job_id ?? result.jobId ?? result.job?.id ?? null

  // Build sqlData for db_result type: map backend field names to SqlResultBlock shape.
  // sqlData is only set when there is a generated SQL or actual columns to display;
  // pure guidance responses (query too short, no tables found) keep sqlData null
  // so the text bubble with the guidance message is shown instead.
  const _isSqlResult = result.result_type === 'db_result'
  const _hasSqlContent = _isSqlResult && !!(result.db_sql || (result.db_columns && result.db_columns.length > 0))
  const _sqlData = _hasSqlContent
    ? {
        sql:               result.db_sql        || '',
        is_valid:          !result.db_error,
        validation_reason: result.db_error       || '',
        db_error:          result.db_error        || null,
        columns:           result.db_columns      || [],
        rows:              result.db_rows         || [],
        matched_tables:    [],
        matched_columns:   [],
        accuracy_hint:     result.accuracy_hint   || null,
        needs_more_info:   result.needs_more_info || false,
        more_info_hint:    result.more_info_hint  || null,
      }
    : null

  const resultMsg = {
    role: "assistant",
    text: result.response_text || result.text || "",
    data: result.data || null,
    options: result.options || [],
    resultType: result.result_type || "",
    sqlData: _sqlData,
    varianceData: result.variance_data || [],
    labelA: result.variance_label_a || "",
    labelB: result.variance_label_b || "",
    llmSummary: result.llm_summary || "",
    instancesData: result.instances_data || [],
    downloadUrl: result.download_url || "",
    downloadLabel: result.download_label || "",
    statusNote: result.status_note || "",
    dbQaData: result.db_qa_data || null,
    // Feedback context — carried forward onto the feedback_prompt message
    // pushed after this one, so a thumbs click can report which query/
    // intent it was actually about.
    feedbackIntent: result.db_intent || result.intent || "",

    // IMPORTANT FIX
    errorDetails: result.error_details || [],
    jobId: jobId,
    ...extra,
  }

  setMessages((prev) => [...prev, resultMsg])
  // After step 2 of the guided workflow the backend clears _guided_sessions and
  // hands control to _session_context (handled by /chat → decide()).
  // Any result_type that is NOT 'guided_input' or 'guided_menu' means the guided
  // report-name step is complete and all subsequent messages must go via /chat.
  if (result.result_type !== 'guided_input' && result.result_type !== 'guided_menu') {
    setIsGuidedFlow(false)
  }
  if (jobId) {
    setTimeout(() => pollForErrors(jobId), 500)
  }

  const shouldShowActionMenu = result.result_type === 'error' || isTerminal
  // Application Database Q&A answers ("what is my role", "how many active
  // users", etc.) are direct factual answers, not part of a report workflow —
  // they get feedback only, no post-action menu. 'db_qa_result' is produced
  // exclusively by backend/db_qa/ (backend/agent/db_qa_router.py) and never
  // by the separate SQL-agent/Oracle NL-to-SQL feature (which always uses
  // 'db_result'), so this is a reliable discriminator, not text matching.
  const isDbQa = result.result_type === 'db_qa_result'

  // A variance table whose AI summary is still being generated is not
  // finished yet: the panel below it is actively filling in. Dropping
  // "Was this helpful?" and the next-action menu underneath it at the usual
  // 800ms buries the analysis the user is waiting for, and asks them to rate
  // a result they cannot see. Hold both until the summary settles —
  // handleSummaryLoaded fires on success, on an empty result, AND on Stop,
  // so every path still reaches the follow-up.
  const awaitingSummary = result.result_type === 'variance_table' && !result.llm_summary
  if (awaitingSummary) {
    // The originating user message is resolved at FLUSH time, from the live
    // list — not captured here — so the follow-up carries the same query it
    // would have had on the 800ms path.
    pendingFollowUpRef.current = {
      intent: resultMsg.feedbackIntent || null,
      resultType: resultMsg.resultType || null,
    }
  } else if (isTerminal && !jobId) {
    // Feedback must render before the action menu. A single scheduled state
    // update appends both in the correct array order in one go — two
    // independent setTimeouts (previously 1000ms for feedback, 800ms for the
    // menu) raced, and the menu's shorter delay always won, putting it first.
    setTimeout(() => {
      setMessages((prev) => {
        const lastUser = [...prev].reverse().find((m) => m.role === 'user')
        const feedbackMsg = {
          role: "feedback_prompt",
          query: lastUser?.text || null,
          intent: resultMsg.feedbackIntent || null,
          resultType: resultMsg.resultType || null,
        }
        return isDbQa ? [...prev, feedbackMsg] : [...prev, feedbackMsg, { role: "action_menu" }]
      })
    }, 800)
  } else if (shouldShowActionMenu) {
    // Non-terminal (e.g. plain 'error') or job-pending results: no feedback
    // prompt applies here, so the menu just shows on its own, unchanged.
    setTimeout(() => {
      setMessages((prev) => [...prev, { role: "action_menu" }])
    }, 800)
  }
}

  // ── Poll for background error enrichment ─────────────────────────────────
  // In pollForErrors, add a counter
const pollForErrors = (jobId) => {
  if (pollIntervalRef.current) {
    clearInterval(pollIntervalRef.current)
    pollIntervalRef.current = null
  }

  let attempts = 0
  const MAX_ATTEMPTS = 150  // 150 × 3s = 7.5 min — covers even slow 5-rule formula jobs

  const tick = async () => {
    attempts++
    if (attempts > MAX_ATTEMPTS) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
      return
    }

    try {
      const res = await fetch(`/status-errors/${jobId}`)
      const data = await res.json()

      // ── Fix: stop polling if job was cleaned up before we got it ──────────
        if (data.status === "not_found") {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
        return
      }

      if (data.status === "done") {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null

        setMessages((prev) =>
          prev.map((msg) => {
            if (String(msg.jobId) !== String(jobId)) return msg

            const cleanText = msg.text
              .replace(/\n*Generating error explanations…/g, '')
              .replace(/\n*Errors Found\s*:\s*\d+/g, '')
              .trimEnd()

            const newErrorDetails = data.error_details || []

            const errorMessages = newErrorDetails
              .map((e) => {
                const ti = e?.table_info ?? {}
                const cell = ti.cell_code || e.cellCode || e.cell || ''
                const msg = e.explanation || ti.validation_error || e.message || ''
                return cell && msg ? `${cell} → ${msg}` : msg
              })
              .filter(Boolean)

            const failureText = errorMessages.length
              ? `\n\nFailure Reason(s):\n${errorMessages.map((m) => `• ${m}`).join('\n')}`
              : ''

            return {
              ...msg,
              text: cleanText + failureText,
              errorDetails: newErrorDetails,
            }
          })
        )

        setTimeout(() => {
          setMessages((prev) => {
            const last = prev[prev.length - 1]
            if (last?.role === 'feedback_prompt') return prev
            const resultIdx = prev.findIndex((m) => String(m.jobId) === String(jobId))
            const resultMsg = resultIdx >= 0 ? prev[resultIdx] : null
            const lastUser = [...prev].reverse().find((m) => m.role === 'user')
            return [...prev, {
              role: 'feedback_prompt',
              query: lastUser?.text || null,
              intent: resultMsg?.feedbackIntent || null,
              resultType: resultMsg?.resultType || null,
            }]
          })
        }, 800)
      }
    } catch (err) {
    }
  }

  pollIntervalRef.current = setInterval(tick, 3000)
}

  // ── Begin tracking a new cancellable request; returns {signal, requestId} ──
  const _beginRequest = () => {
    const controller = new AbortController()
    const requestId = crypto.randomUUID()
    activeRequestRef.current = { controller, requestId }
    return { signal: controller.signal, requestId }
  }

  // Clears the active-request marker only if it still points at this request
  // (guards against a stray call from an already-superseded request).
  const _endRequest = (requestId) => {
    if (activeRequestRef.current?.requestId === requestId) {
      activeRequestRef.current = null
    }
  }

  // ── Stop button — cancel whatever request is currently in flight ─────────
  const handleStop = () => {
    const active = activeRequestRef.current
    if (!active) return
    active.controller.abort()
    stopRequest(active.requestId)
    activeRequestRef.current = null
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
    setIsLoading(false)
  }

  // ── Free-text chat ────────────────────────────────────────────────────────
  const submitChatMessage = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    // Capture history BEFORE appending the current user message
    const recentHistory = _getRecentHistory(messages)

    if (pollIntervalRef.current) {
  clearInterval(pollIntervalRef.current)
  pollIntervalRef.current = null
}

    setMessages((prev) => [...prev, { role: 'user', text: trimmed }])
    setIsLoading(true)
    const { signal, requestId } = _beginRequest()

    try {
      const result = await sendMessage(
        trimmed,
        sessionId.current,
        _aspSession || null,
        _loginId || null,
        _uid || null,
        _roleId || null,
        recentHistory,
        { signal, requestId, tenantId: _tenantId || null, domain: _domain || null, jwt: jwtRef.current || null },
      )
      _pushResult(result)
    } catch (err) {
      if (err.name === 'AbortError') return
      setIsGuidedFlow(false)
      setMessages((prev) => [
        ...prev,
        { role: 'error', text: err.message || 'Something went wrong. Please try again.' },
      ])
    } finally {
      _endRequest(requestId)
      setIsLoading(false)
    }
  }


  // ── Guided workflow step ──────────────────────────────────────────────────
  const submitGuidedStep = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    if (pollIntervalRef.current) {
  clearInterval(pollIntervalRef.current)
  pollIntervalRef.current = null
}
    setMessages((prev) => [...prev, { role: 'user', text: trimmed }])
    setIsLoading(true)
    const { signal, requestId } = _beginRequest()

    try {
      const result = await sendGuidedMessage(
        trimmed,
        sessionId.current,
        _aspSession || null,
        _loginId || null,
        _uid || null,
        _roleId || null,
        { signal, requestId, tenantId: _tenantId || null, domain: _domain || null, jwt: jwtRef.current || null },
      )
      _pushResult(result)
    } catch (err) {
      if (err.name === 'AbortError') return
      setIsGuidedFlow(false)
      setMessages((prev) => [
        ...prev,
        { role: 'error', text: err.message || 'Something went wrong. Please try again.' },
      ])
    } finally {
      _endRequest(requestId)
      setIsLoading(false)
    }
  }

  // ── Start guided flow via welcome card action button ────────────────────
  const handleGuidedAction = async (action) => {
    if (isLoading) return
    setIsGuidedFlow(true)
    setMessages((prev) => [...prev, { role: 'user', text: action }])
    setIsLoading(true)
    const { signal, requestId } = _beginRequest()
    try {
      const result = await sendGuidedMessage(
        action,
        sessionId.current,
        _aspSession || null,
        _loginId || null,
        _uid || null,
        _roleId || null,
        { signal, requestId, tenantId: _tenantId || null, domain: _domain || null, jwt: jwtRef.current || null },
      )
      _pushResult(result)
    } catch (err) {
      if (err.name === 'AbortError') return
      setIsGuidedFlow(false)
      setMessages((prev) => [...prev, { role: 'error', text: err.message }])
    } finally {
      _endRequest(requestId)
      setIsLoading(false)
    }
  }

  // ── Compare Instances button ──────────────────────────────────────────────
  const handleCompareInstances = async (idxA, idxB) => {
    if (isLoading) return
    setMessages((prev) => [...prev, { role: 'user', text: 'Compare Instances' }])
    setIsLoading(true)
    const { signal, requestId } = _beginRequest()
    try {
      const result = await compareInstances(sessionId.current, idxA, idxB, { signal, requestId })
      _pushResult(result)
    } catch (err) {
      if (err.name === 'AbortError') return
      setIsGuidedFlow(false)
      setMessages((prev) => [
        ...prev,
        { role: 'error', text: err.message || 'Comparison failed. Please try again.' },
      ])
    } finally {
      _endRequest(requestId)
      setIsLoading(false)
    }
  }

  // ── Explain a single error category (Formula / XBRL Schema) ───────────────
  // offset (default 0) is 0 for the initial "Explain X Errors" button click
  // (always starts the batch sequence fresh for this file+category) and is
  // set explicitly when called from the "Explain Next Errors" button
  // rendered on a previous batch's result message (see MessageBubble.jsx),
  // continuing from where that batch left off — never re-requesting
  // already-explained errors.
  const handleExplainCategory = async (category, errorFilePath, formId = null, reportName = null, offset = 0) => {
    if (isLoading) return
    setIsLoading(true)
    const { signal, requestId } = _beginRequest()
    try {
      const result = await explainErrorCategory(errorFilePath, category, formId, reportName, { signal, requestId, offset })
      _pushResult(result, {
        batchCategory: category,
        batchErrorFilePath: errorFilePath,
        batchFormId: formId,
        batchReportName: reportName,
      })
    } catch (err) {
      if (err.name === 'AbortError') return
      setMessages((prev) => [
        ...prev,
        { role: 'error', text: err.message || 'Failed to generate explanations. Please try again.' },
      ])
    } finally {
      _endRequest(requestId)
      setIsLoading(false)
    }
  }



  // ── AI variance summary arrived (fetched after the table) ────────────────
  // Store it on the message so it survives a reload — and so the fetch is
  // never repeated. noAutoSummary is set even for an empty result: that
  // records "we already tried", which is what stops the next page load from
  // asking the model all over again.
  const handleSummaryLoaded = (idx, text) => {
    const followUp = pendingFollowUpRef.current
    pendingFollowUpRef.current = null
    setMessages((prev) => {
      const updated = prev.map((m, i) => (
        i === idx ? { ...m, llmSummary: text || m.llmSummary || '', noAutoSummary: true } : m
      ))
      // Deferred from _pushResult: the comparison is only really finished now
      // that the analysis has stopped writing. Guarded against a double
      // append if this fires twice for the same message.
      if (!followUp) return updated
      if (updated[updated.length - 1]?.role === 'feedback_prompt'
          || updated[updated.length - 1]?.role === 'action_menu') return updated
      const lastUser = [...updated].reverse().find((m) => m.role === 'user')
      return [
        ...updated,
        {
          role: 'feedback_prompt',
          query: lastUser?.text || null,
          intent: followUp.intent,
          resultType: followUp.resultType,
        },
        { role: 'action_menu' },
      ]
    })
  }

  // ── Feedback after completed action ──────────────────────────────────────
  const handleFeedback = (response, context = {}) => {
    sendFeedback(response === 'yes' ? 'up' : 'down', {
      query: context.query ?? null,
      intent: context.intent ?? null,
      resultType: context.resultType ?? null,
      sessionId: sessionId.current,
    })
    if (response === 'yes') {
      setMessages((prev) => [...prev, { role: 'feedback_positive' }])
    } else {
      setMessages((prev) => [...prev, { role: 'feedback_negative' }])
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
      <main className="chat-area">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSuggestion={handleSuggestion}
          onGuidedAction={handleGuidedAction}
          onCompare={handleCompareInstances}
          onFeedback={handleFeedback}
          onExplainCategory={handleExplainCategory}
          onSummaryLoaded={handleSummaryLoaded}
          allowedActions={allowedActions}
        />
      </main>

      <footer className="input-bar">
        {isGuidedFlow && (
          <div className="guided-mode-indicator">🧭 Guided mode — answer the question above</div>
        )}
        <form className="input-form" onSubmit={handleSubmit}>
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
          {isLoading ? (
            <button
              type="button"
              className="send-btn stop-btn"
              onClick={handleStop}
              aria-label="Stop generating"
              title="Stop generating"
            >
              <StopIcon />
            </button>
          ) : (
            <button
              type="submit"
              className="send-btn"
              disabled={!inputText.trim()}
              aria-label="Send message"
            >
              <SendIcon />
            </button>
          )}
        </form>
        {/* AI disclaimer — required on every AI-facing surface. Kept inside the
            input bar so it stays pinned below the composer and is visible on
            every screen, rather than scrolling away with the conversation. */}
        <p className="ai-disclaimer">
          AI-generated responses may be inaccurate — please verify important
          details against the application before acting on them.
        </p>
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

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
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
 