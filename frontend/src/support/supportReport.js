/**
 * supportReport.js — pure logic behind "Report an issue" (no React, no network).
 *
 * Kept separate from the component so validation, the reference id, the
 * response-code mapping and the opt-in question/answer extraction can be
 * tested directly and cannot drift from what the backend (POST /support-request)
 * actually accepts.
 */

// Wire values accepted by the backend, in the order they are offered.
export const CATEGORIES = ['incorrect_answer', 'technical_problem', 'missing_information', 'other']

// Backend limits: description 10-2000 (after trimming); optional text is clipped there too.
export const DESCRIPTION_MIN = 10
export const DESCRIPTION_MAX = 2000
export const LAST_QUERY_MAX = 500
export const ANSWER_MAX = 1000

/**
 * Per-code presentation. `key` is the i18n key of the message; `kind` drives the
 * styling and which actions are offered:
 *   success  accepted into the support queue (never "delivered")
 *   auth     the user must go through the existing sign-in / OTP flow
 *   retry    the same report can be sent again with the SAME reference id
 *   final    nothing to retry (fix the input, or the feature is unavailable)
 */
export const CODE_INFO = {
  ok:              { key: 'support.report.code.ok',              kind: 'success' },
  duplicate:       { key: 'support.report.code.duplicate',       kind: 'success' },
  invalid_input:   { key: 'support.report.code.invalid_input',   kind: 'final' },
  session_required:{ key: 'support.report.code.session_required',kind: 'auth' },
  session_expired: { key: 'support.report.code.session_expired', kind: 'auth' },
  otp_required:    { key: 'support.report.code.otp_required',    kind: 'auth' },
  not_available:   { key: 'support.report.code.not_available',   kind: 'final' },
  rate_limited:    { key: 'support.report.code.rate_limited',    kind: 'retry' },
  queue_failed:    { key: 'support.report.code.queue_failed',    kind: 'retry' },
  unreachable:     { key: 'support.report.code.unreachable',     kind: 'retry' },
  upstream_error:  { key: 'support.report.code.upstream_error',  kind: 'retry' },
  outcome_unknown: { key: 'support.report.code.outcome_unknown', kind: 'retry' },
  internal_error:  { key: 'support.report.code.internal_error',  kind: 'retry' },
}

/** Presentation for a code; anything unrecognised is treated as an unconfirmed failure, never success. */
export function infoForCode(code) {
  return CODE_INFO[code] || CODE_INFO.outcome_unknown
}

/**
 * New client-generated reference id, matching the backend pattern ^SR-[A-Z0-9]{6,24}$.
 * Created once per report and re-sent on every retry of that report, which is
 * what lets the backend recognise a repeat instead of queuing it twice.
 */
export function newReferenceId() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  const bytes = new Uint8Array(12)
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) crypto.getRandomValues(bytes)
  else for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256)
  let id = 'SR-'
  for (const b of bytes) id += alphabet[b % alphabet.length]
  return id
}

/** Length that counts toward the limits: the trimmed text, as the backend measures it. */
export function descriptionLength(text) {
  return (text || '').trim().length
}

/**
 * @returns {null | 'support.report.err.tooShort' | 'support.report.err.tooLong'}
 *          the i18n key of the problem, or null when the description is acceptable.
 */
export function validateDescription(text) {
  const n = descriptionLength(text)
  if (n < DESCRIPTION_MIN) return 'support.report.err.tooShort'
  if (n > DESCRIPTION_MAX) return 'support.report.err.tooLong'
  return null
}

/**
 * The most recent user question and the most recent assistant answer, clipped.
 * Called ONLY when the user ticked "Include my last question and answer" — it
 * is never run speculatively and never stored. Only these two texts are ever
 * taken; the rest of the conversation is not read.
 */
export function lastExchange(messages) {
  let question = ''
  let answer = ''
  for (let i = (messages || []).length - 1; i >= 0 && !(question && answer); i--) {
    const m = messages[i]
    if (!m) continue
    const text = String(m.textEn || m.text || '').trim()
    if (!text) continue
    if (m.role === 'assistant' && !answer) answer = text
    else if (m.role === 'user' && !question) question = text
  }
  return { lastQuery: question.slice(0, LAST_QUERY_MAX), chatbotAnswer: answer.slice(0, ANSWER_MAX) }
}

/**
 * One report's lifecycle, independent of React.
 *
 *   status: 'idle' | 'sending' | 'done' | 'failed'
 *
 * Owns the three things that must not depend on rendering: the reference id (one
 * per report, reused by every retry), the in-flight guard (a second submit while
 * one is running does nothing, so a double click cannot send two requests), and
 * the opt-in question/answer read (only when `includeQa` is true, only at submit).
 * Never retries by itself: each submit() call makes exactly one request.
 *
 * @param {{ submit: Function }} deps  `submit` is api.submitSupportRequest (injected so tests need no network)
 */
export function createSupportReport({ submit }) {
  const referenceId = newReferenceId()
  const listeners = new Set()
  let state = { status: 'idle', result: null }
  let inFlight = false
  const set = (patch) => { state = { ...state, ...patch }; listeners.forEach((l) => l()) }
  return {
    referenceId,
    getState: () => state,
    subscribe: (l) => { listeners.add(l); return () => listeners.delete(l) },
    async submit({ description, category, includeQa, lang, aspSession, getMessages }) {
      if (inFlight || state.status === 'done') return state
      if (validateDescription(description)) return state       // the form shows the validation message
      inFlight = true
      set({ status: 'sending' })
      const qa = includeQa ? lastExchange(getMessages ? getMessages() : []) : {}
      let res
      try {
        res = await submit({
          description: description.trim(), category, referenceId, lang,
          aspSession: aspSession || null, lastQuery: qa.lastQuery, chatbotAnswer: qa.chatbotAnswer,
        })
      } catch {
        res = { ok: false, code: 'outcome_unknown', referenceId, duplicate: false, retryable: true, field: '' }
      }
      inFlight = false
      set({ status: res.ok ? 'done' : 'failed', result: res })
      return state
    },
  }
}
