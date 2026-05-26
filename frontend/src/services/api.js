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
 * Directly execute a pre-staged instance comparison.
 *
 * Called when the user clicks "Compare Instances" in the dropdown UI.
 * Hits /compare-execute which bypasses intent detection entirely and runs
 * the XBRL variance pipeline using the session's stored instance paths.
 *
 * @param {string} sessionId - Session ID that holds the staged comparison state.
 * @param {number} instanceA - 0-based index of the first instance.
 * @param {number} instanceB - 0-based index of the second instance.
 * @returns {Promise<object>} - ChatResponse (variance_table or error).
 */
export async function compareInstances(sessionId, instanceA, instanceB) {
  const res = await fetch(`${BASE_URL}/compare-execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      instance_a: instanceA,
      instance_b: instanceB,
    }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Compare error (${res.status})`)
  }

  return res.json()
}

/**
 * Send a natural language message to the FastAPI /chat endpoint.
 *
 * @param {string} message - User query text.
 * @param {string|null} sessionId - Optional session ID for context.
 * @returns {Promise<{intent: string, report_name: string|null, response_text: string, need_clarification: boolean}>}
 * @throws {Error} - With a user-friendly message on failure.
 */
export async function sendMessage(message, sessionId = null, aspSession = null, loginId = null, conversationHistory = []) {
  const body = { message }
  if (sessionId)                    body.session_id           = sessionId
  if (aspSession)                   body.asp_session          = aspSession
  if (loginId)                      body.login_id             = loginId
  if (conversationHistory?.length)  body.conversation_history = conversationHistory

  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Server error (${res.status})`)
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
 * @returns {Promise<object>}
 */
export async function sendGuidedMessage(message, sessionId = null, aspSession = null, loginId = null) {
  const body = { message }
  if (sessionId)  body.session_id  = sessionId
  if (aspSession) body.asp_session = aspSession
  if (loginId)    body.login_id    = loginId

  const res = await fetch(`${BASE_URL}/guided`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Guided workflow error (${res.status})`)
  }

  return await res.json()
}

/**
 * Send a recorded audio Blob to the FastAPI /speech-to-text endpoint,
 * which proxies it to Sarvam AI.
 *
 * @param {Blob} audioBlob - Raw audio recorded by MediaRecorder.
 * @returns {Promise<string>} - Transcribed text.
 * @throws {Error} - With a user-friendly message on failure.
 */
export async function transcribeAudio(audioBlob) {
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
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Transcription error (${res.status})`)
  }

  const data = await res.json()
  return data.transcript ?? ''
}

