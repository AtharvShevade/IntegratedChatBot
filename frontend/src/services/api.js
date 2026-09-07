/**
 * api.js — All HTTP calls from the React frontend.
 *
 * During development, Vite proxies /chat and /speech-to-text to
 * http://localhost:8001, so no CORS issues arise.
 *
 * In production, set VITE_API_BASE_URL to the deployed backend origin.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

/**
 * Build an Error carrying an i18n KEY for its fallback wording.
 *
 * This module has no React context and therefore no language, so it cannot
 * translate. It records WHICH message applies and the component resolves it
 * with the active language. A `detail` from the backend still wins -- that is
 * a real server message, not a generic fallback.
 */
function _err(detail, i18nKey) {
  const e = new Error(detail || '')
  e.i18nKey = i18nKey
  return e
}

/**
 * Fetch the subset of guided-menu actions the given identity may see/perform.
 * Side-effect-free — does not touch any conversation session, unlike POSTing
 * a sentinel message through /guided.
 *
 * @param {string|null} loginId
 * @param {object} [opts]
 * @param {string|null} [opts.tenantId] - APP_VERSION=6.0 only.
 * @param {string|null} [opts.domain] - APP_VERSION=6.0 only, fallback if tenantId absent.
 * @returns {Promise<string[]>} allowed action labels, or [] on failure.
 */
export async function getAllowedActions(loginId, opts = {}) {
  const { tenantId, domain } = opts
  const params = new URLSearchParams()
  if (loginId)  params.set('login_id', loginId)
  if (tenantId) params.set('tenant_id', tenantId)
  if (domain)   params.set('domain', domain)
  const qs = params.toString()
  const res = await fetch(`${BASE_URL}/allowed-actions${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw _err('', 'errors.fetchActions')
  const data = await res.json()
  return Array.isArray(data?.actions) ? data.actions : []
}

/**
 * Ask the backend to cancel an in-flight request by its request_id.
 * Best-effort: safe to call even if the request has already finished.
 *
 * @param {string} requestId
 */
export async function stopRequest(requestId) {
  if (!requestId) return
  try {
    await fetch(`${BASE_URL}/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: requestId }),
    })
  } catch {
    // Best-effort — the client-side abort() already stopped the UI wait.
  }
}

/**
 * Send a thumbs up/down rating for a completed assistant response.
 * Best-effort, fire-and-forget: a failure here should never surface to the
 * user or break the chat flow, so this never throws.
 *
 * @param {'up'|'down'} rating
 * @param {object} [context]
 * @param {string|null} [context.query] - The user question this feedback is about.
 * @param {string|null} [context.intent] - Detected intent for that response, if known.
 * @param {string|null} [context.resultType] - e.g. db_qa_result, final, error.
 * @param {string|null} [context.sessionId]
 */
export async function sendFeedback(rating, context = {}) {
  const { query = null, intent = null, resultType = null, sessionId = null } = context
  try {
    await fetch(`${BASE_URL}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rating,
        query,
        intent,
        result_type: resultType,
        session_id: sessionId,
      }),
    })
  } catch {
    // Best-effort — feedback loss should never affect the chat UI.
  }
}

/**
 * Directly execute a pre-staged instance comparison.
 *
 * Called when the user clicks "Compare Instances" in the dropdown UI.
 * Hits /compare-execute which bypasses intent detection entirely and runs
 * the XBRL variance pipeline using the session's stored instance paths.
 *
 * @param {string} sessionId - Session ID that holds the staged comparison state.
 * @param {number} instanceA - 0-based index of the first instance.
 * @param {number} instanceB - 0-based index of the second instance.
 * @param {object} [opts]
 * @param {AbortSignal} [opts.signal]
 * @param {string} [opts.requestId]
 * @returns {Promise<object>} - ChatResponse (variance_table or error).
 */
export async function compareInstances(sessionId, instanceA, instanceB, opts = {}) {
  const { signal, requestId, lang } = opts
  const body = {
    session_id: sessionId,
    instance_a: instanceA,
    instance_b: instanceB,
    request_id: requestId ?? null,
  }
  // Same contract as sendMessage: omitted / 'en' takes the exact English path.
  if (lang && lang !== 'en') body.lang = lang
  const res = await fetch(`${BASE_URL}/compare-execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw _err(body.detail, 'errors.compareFailed')
  }

  return res.json()
}

/**
 * Fetch the AI narrative for a variance table that is already on screen.
 *
 * /compare-execute returns the table and chart immediately, with only an
 * 8-second budget for the summary — which a CPU-hosted Ollama cannot meet
 * (~140s measured). This second call runs the same generator with a
 * realistic budget so the AI Analysis panel fills in when it is ready,
 * instead of the table waiting minutes for an optional paragraph.
 *
 * Never throws: a missing summary is not an error state — the table and
 * chart are complete without it.
 *
 * @param {Array}  rows - variance_data rows exactly as received.
 * @param {string} labelA
 * @param {string} labelB
 * @param {string} reportName
 * @param {object} [opts]
 * @param {AbortSignal} [opts.signal]
 * @param {string} [opts.requestId] - enables Stop: /compare-summary registers
 *   the task under this id, so POST /stop can cancel the in-flight LLM call
 *   server-side rather than just abandoning it client-side.
 * @returns {Promise<string>} the summary text, or '' if unavailable.
 */
export async function fetchCompareSummary(rows, labelA, labelB, reportName, opts = {}) {
  const { signal, requestId, lang } = opts
  try {
    const res = await fetch(`${BASE_URL}/compare-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rows: (rows ?? []).map((r) => ({
          concept:     r.concept ?? '',
          val_a:       r.val_a ?? null,
          val_b:       r.val_b ?? null,
          diff:        r.diff ?? null,
          pct_change:  r.pct_change ?? null,
          significant: Boolean(r.significant),
          // Regulatory-importance context, echoed back so the async narrative
          // names the same supervisory section the table on screen was ranked
          // by. Empty for a return whose taxonomy could not be read, and the
          // backend prompt then falls back to plain variance wording.
          section:         r.section ?? '',
          importance_tier: r.importance_tier ?? '',
          mandated_by:     Array.isArray(r.mandated_by) ? r.mandated_by.slice(0, 8) : [],
          // Needed to SELECT and describe the facts server-side: concept_base
          // drives the max-3-variants-per-concept cap, context_key locates the
          // parent row for share-of-total, unit decides whether ₹ Cr applies,
          // and priority is the 60/40 order the selection slices.
          concept_base:       r.concept_base ?? r.concept ?? '',
          context_key:        r.context_key ?? 'BASE',
          unit:               r.unit ?? '',
          section_code:       r.section_code ?? '',
          importance:         r.importance ?? null,
          priority:           r.priority ?? null,
          importance_matched: Boolean(r.importance_matched),
        })),
        label_a:     labelA ?? '',
        label_b:     labelB ?? '',
        report_name: reportName ?? '',
        request_id:  requestId ?? null,
        // The AI narrative is model-authored, so it is translated at runtime by
        // the existing boundary. Omitted / 'en' leaves it in English.
        ...(lang && lang !== 'en' ? { lang } : {}),
      }),
      signal,
    })
    if (!res.ok) return ''
    const data = await res.json().catch(() => ({}))
    return data.llm_summary ?? ''
  } catch {
    return ''
  }
}

/**
 * Send a natural language message to the FastAPI /chat endpoint.
 *
 * @param {string} message - User query text.
 * @param {string|null} sessionId - Optional session ID for context.
 * @param {string|null} aspSession
 * @param {string|null} loginId
 * @param {string|null} userId
 * @param {string|null} roleId
 * @param {Array} conversationHistory
 * @param {object} [opts]
 * @param {AbortSignal} [opts.signal]
 * @param {string} [opts.requestId]
 * @param {string|null} [opts.tenantId] - APP_VERSION=6.0 only.
 * @param {string|null} [opts.domain] - APP_VERSION=6.0 only, fallback if tenantId absent.
 * @param {string|null} [opts.jwt] - APP_VERSION=6.0 only; replaces asp_session for .NET API calls.
 * @returns {Promise<{intent: string, report_name: string|null, response_text: string, need_clarification: boolean}>}
 * @throws {Error} - With a user-friendly message on failure.
 */
export async function sendMessage(
  message,
  sessionId = null,
  aspSession = null,
  loginId = null,
  userId = null,
  roleId = null,
  conversationHistory = [],
  opts = {},
) {
  const { signal, requestId, tenantId, domain, jwt, lang } = opts
  const body = { message }
  // Language the user is writing in. Omitted / 'en' => the backend takes the
  // exact English path it took before multilingual support existed.
  if (lang && lang !== 'en')        body.lang                 = lang
  if (sessionId)                    body.session_id           = sessionId
  if (aspSession)                   body.asp_session          = aspSession
  if (loginId)                      body.login_id             = loginId
  if (userId)                       body.user_id              = userId
  if (roleId)                       body.role_id              = roleId
  if (conversationHistory?.length)  body.conversation_history = conversationHistory
  if (requestId)                    body.request_id           = requestId
  if (tenantId)                     body.tenant_id            = tenantId
  if (domain)                       body.domain               = domain
  if (jwt)                          body.jwt                  = jwt

  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw _err(body.detail, 'errors.requestFailed')
  }

  return await res.json()
}

/**
 * Send one step of the guided workflow to POST /guided.
 * Pass message="__GUIDED_START__" to open the action menu.
 *
 * @param {string} message
 * @param {string|null} sessionId
 * @param {string|null} aspSession
 * @param {string|null} loginId
 * @param {string|null} userId
 * @param {string|null} roleId
 * @param {object} [opts]
 * @param {AbortSignal} [opts.signal]
 * @param {string} [opts.requestId]
 * @param {string|null} [opts.tenantId] - APP_VERSION=6.0 only.
 * @param {string|null} [opts.domain] - APP_VERSION=6.0 only, fallback if tenantId absent.
 * @param {string|null} [opts.jwt] - APP_VERSION=6.0 only; replaces asp_session for .NET API calls.
 * @returns {Promise<object>}
 */
export async function sendGuidedMessage(message, sessionId = null, aspSession = null, loginId = null, userId = null, roleId = null, opts = {}) {
  const { signal, requestId, tenantId, domain, jwt, lang } = opts
  const body = { message }
  // Language the user is writing in. Omitted / 'en' => the backend takes the
  // exact English path it took before multilingual support existed.
  if (lang && lang !== 'en')        body.lang                 = lang
  if (sessionId)  body.session_id  = sessionId
  if (aspSession) body.asp_session = aspSession
  if (loginId)    body.login_id    = loginId
  if (userId)     body.user_id     = userId
  if (roleId)     body.role_id     = roleId
  if (requestId)  body.request_id  = requestId
  if (tenantId)   body.tenant_id   = tenantId
  if (domain)     body.domain      = domain
  if (jwt)        body.jwt         = jwt

  const res = await fetch(`${BASE_URL}/guided`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw _err(err.detail, 'errors.requestFailed')
  }

  return await res.json()
}

/**
 * Send a recorded audio Blob to the FastAPI /speech-to-text endpoint,
 * which forwards it to the remote Whisper service (backend/stt).
 *
 * @param {Blob} audioBlob - Raw audio recorded by MediaRecorder.
 * @param {object} [opts]
 * @param {AbortSignal} [opts.signal]
 * @param {string} [opts.lang] - Selected UI language; the STT language hint.
 * @param {string} [opts.requestId] - Lets /stop cancel a slow transcription.
 * @returns {Promise<string>} - Transcribed text, in the SPOKEN language.
 * @throws {Error} - With a user-friendly message on failure.
 */
export async function transcribeAudio(audioBlob, opts = {}) {
  const { signal, lang, requestId } = opts
  const formData = new FormData()
  // Give the file a name with the correct extension based on MIME type
  const ext = audioBlob.type.includes('webm') ? 'webm'
    : audioBlob.type.includes('ogg')  ? 'ogg'
    : audioBlob.type.includes('mp4')  ? 'mp4'
    : 'audio'
  formData.append('file', audioBlob, `recording.${ext}`)
  // Unlike /chat, English is sent EXPLICITLY. STT must be told which language
  // is being spoken -- there is no "leave it in English" default to fall back
  // on the way there is for translation, and Whisper's own detection is
  // unreliable on short clips (measured 0.35-0.63 confidence on non-speech).
  if (lang)      formData.append('lang', lang)
  if (requestId) formData.append('request_id', requestId)

  const res = await fetch(`${BASE_URL}/speech-to-text`, {
    method: 'POST',
    body: formData,
    // Do NOT set Content-Type manually — browser sets it with the boundary
    signal,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw _err(body.detail, 'voice.transcribeFailed')
  }

  const data = await res.json()
  return data.transcript ?? ''
}

/**
 * Request on-demand explanations for a single error category
 * (formula_error | xbrl_schema | dimensional). Triggered when the user
 * clicks an "Explain ... Errors" button in the Error Summary panel.
 *
 * @param {string} errorFilePath - Absolute path to the error HTML/XML file
 *                                  (from error_category_counts.error_file_path).
 * @param {string} category - One of "formula_error", "xbrl_schema", "dimensional".
 * @param {string|null} formId - Report form ID (needed for xbrl_schema 4000-series tagging).
 * @param {string|null} reportName - Report display name (for the response header).
 * @param {object} [opts]
 * @param {AbortSignal} [opts.signal]
 * @param {string} [opts.requestId]
 * @returns {Promise<object>} - ChatResponse-shaped object with error_details populated.
 */
export async function explainErrorCategory(errorFilePath, category, formId = null, reportName = null, opts = {}) {
  const { signal, requestId, offset, lang } = opts
  const body = { error_file_path: errorFilePath, category }
  if (lang && lang !== 'en') body.lang = lang
  if (formId)     body.form_id     = formId
  if (reportName) body.report_name = reportName
  if (requestId)  body.request_id  = requestId
  if (offset)     body.offset      = offset
  // Use the same BASE_URL as sendMessage — relies on Vite proxy in dev,
  // VITE_API_BASE_URL in production. Do NOT use a hardcoded localhost fallback
  // here (unlike the polling fetch in App.jsx which correctly uses port 8001).
  const res = await fetch(`${BASE_URL}/explain-category`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw _err(err.detail, 'errors.explanationFailed')
  }
  return await res.json()
}
