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
 * Fetch the subset of guided-menu actions the given identity may see/perform.
 * Side-effect-free — does not touch any conversation session, unlike POSTing
 * a sentinel message through /guided.
 *
 * @param {string|null} loginId
 * @param {string|null} tenantId
 * @returns {Promise<string[]>} allowed action labels, or [] on failure.
 */
export async function getAllowedActions(loginId, tenantId) {
  const params = new URLSearchParams()
  if (loginId)  params.set('login_id', loginId)
  if (tenantId) params.set('tenant_id', tenantId)
  const qs = params.toString()
  const res = await fetch(`${BASE_URL}/allowed-actions${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw new Error('Failed to fetch allowed actions')
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
 * @param {string|null} [opts.tenantId] - 6.0 only; resolved client-side from JWT claim.
 * @param {string|null} [opts.jwt] - 6.0 only; raw JWT for server-side Bearer auth.
 * @returns {Promise<object>} - ChatResponse (variance_table or error).
 */
export async function compareInstances(sessionId, instanceA, instanceB, opts = {}) {
  const { signal, requestId, tenantId, jwt } = opts
  const body = {
    session_id: sessionId,
    instance_a: instanceA,
    instance_b: instanceB,
    request_id: requestId ?? null,
  }
  if (tenantId) body.tenant_id = tenantId
  if (jwt)      body.jwt       = jwt
  const res = await fetch(`${BASE_URL}/compare-execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? 'We could not compare those instances right now. Please try again.')
  }

  return res.json()
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
 * @param {string|null} [opts.tenantId] - 6.0 only; resolved client-side from JWT claim.
 * @param {string|null} [opts.jwt] - 6.0 only; raw JWT for server-side Bearer auth.
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
  const { signal, requestId, tenantId, jwt } = opts
  const body = { message }
  if (sessionId)                    body.session_id           = sessionId
  if (aspSession)                   body.asp_session          = aspSession
  if (loginId)                      body.login_id             = loginId
  if (userId)                       body.user_id              = userId
  if (roleId)                       body.role_id              = roleId
  if (conversationHistory?.length)  body.conversation_history = conversationHistory
  if (requestId)                    body.request_id           = requestId
  if (tenantId)                     body.tenant_id            = tenantId
  if (jwt)                          body.jwt                  = jwt

  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? 'We could not process your request right now. Please try again.')
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
 * @param {string|null} [opts.tenantId] - 6.0 only; resolved client-side from JWT claim.
 * @param {string|null} [opts.jwt] - 6.0 only; raw JWT for server-side Bearer auth.
 * @returns {Promise<object>}
 */
export async function sendGuidedMessage(message, sessionId = null, aspSession = null, loginId = null, userId = null, roleId = null, opts = {}) {
  const { signal, requestId, tenantId, jwt } = opts
  const body = { message }
  if (sessionId)  body.session_id  = sessionId
  if (aspSession) body.asp_session = aspSession
  if (loginId)    body.login_id    = loginId
  if (userId)     body.user_id     = userId
  if (roleId)     body.role_id     = roleId
  if (requestId)  body.request_id  = requestId
  if (tenantId)   body.tenant_id   = tenantId
  if (jwt)        body.jwt         = jwt

  const res = await fetch(`${BASE_URL}/guided`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'We could not process your request right now. Please try again.')
  }

  return await res.json()
}

/**
 * Send a recorded audio Blob to the FastAPI /speech-to-text endpoint,
 * which proxies it to Sarvam AI.
 *
 * @param {Blob} audioBlob - Raw audio recorded by MediaRecorder.
 * @param {object} [opts]
 * @param {AbortSignal} [opts.signal]
 * @returns {Promise<string>} - Transcribed text.
 * @throws {Error} - With a user-friendly message on failure.
 */
export async function transcribeAudio(audioBlob, opts = {}) {
  const { signal } = opts
  const formData = new FormData()
  // Give the file a name with the correct extension based on MIME type
  const ext = audioBlob.type.includes('webm') ? 'webm'
    : audioBlob.type.includes('ogg')  ? 'ogg'
    : audioBlob.type.includes('mp4')  ? 'mp4'
    : 'audio'
  formData.append('file', audioBlob, `recording.${ext}`)

  const res = await fetch(`${BASE_URL}/speech-to-text`, {
    method: 'POST',
    body: formData,
    // Do NOT set Content-Type manually — browser sets it with the boundary
    signal,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? 'Sorry, voice transcription failed. Please try again.')
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
 * @param {string|null} [opts.tenantId] - 6.0 only; resolved client-side from JWT claim.
 * @returns {Promise<object>} - ChatResponse-shaped object with error_details populated.
 */
export async function explainErrorCategory(errorFilePath, category, formId = null, reportName = null, opts = {}) {
  const { signal, requestId, tenantId } = opts
  const body = { error_file_path: errorFilePath, category }
  if (formId)     body.form_id     = formId
  if (reportName) body.report_name = reportName
  if (requestId)  body.request_id  = requestId
  if (tenantId)   body.tenant_id   = tenantId
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
    throw new Error(err.detail ?? 'We could not load the explanation right now. Please try again.')
  }
  return await res.json()
}
