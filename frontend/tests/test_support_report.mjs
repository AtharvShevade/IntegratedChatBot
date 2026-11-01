/**
 * Tests for the "Report an issue" feature (frontend only; no network, no browser).
 *
 *   node frontend/tests/test_support_report.mjs
 *
 * The project has no test runner or DOM, so — like the other scripts in this folder — this is a
 * standalone script. The sources are bundled with esbuild (already installed with Vite) and the
 * components are rendered with react-dom/server; the interactive behaviour (double submit, retry,
 * opt-in) lives in a framework-free controller and is driven directly. `fetch` is replaced by a fake,
 * so nothing here can reach a server or send an email.
 */
import { createRequire } from 'node:module'
import { readFileSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, dirname } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import assert from 'node:assert/strict'

const here = dirname(fileURLToPath(import.meta.url))
const root = join(here, '..')
const require = createRequire(join(root, 'package.json'))
const esbuild = require('esbuild')

// ── bundle the code under test ────────────────────────────────────────────
const out = mkdtempSync(join(tmpdir(), 'support-report-'))
const entry = join(out, 'entry.jsx')
writeFileSync(entry, `
export * from ${JSON.stringify(join(root, 'src/support/supportReport.js').replace(/\\/g, '/'))}
export { submitSupportRequest } from ${JSON.stringify(join(root, 'src/services/api.js').replace(/\\/g, '/'))}
export { SupportReportForm, SupportReportOffer, SupportReportContext } from ${JSON.stringify(join(root, 'src/components/SupportReport.jsx').replace(/\\/g, '/'))}
export { makeT, isRtl, LanguageContext } from ${JSON.stringify(join(root, 'src/i18n.js').replace(/\\/g, '/'))}
export { default as React } from 'react'
export { renderToStaticMarkup } from 'react-dom/server'
`)
await esbuild.build({
  entryPoints: [entry], outfile: join(out, 'bundle.mjs'), bundle: true, format: 'esm', platform: 'node',
  banner: { js: "import { createRequire as __cr } from 'node:module'; const require = __cr(import.meta.url);" },
  jsx: 'automatic', nodePaths: [join(root, 'node_modules')], logLevel: 'error',
  define: { 'import.meta.env.VITE_API_BASE_URL': '"http://backend.test"' },
})
const M = await import(pathToFileURL(join(out, 'bundle.mjs')).href)
const { React, renderToStaticMarkup, makeT, isRtl, LanguageContext } = M

const say = console.log.bind(console)
let passed = 0
const failures = []
async function test(name, fn) {
  try { await fn(); passed++ } catch (e) { failures.push([name, e]); say(`  FAIL ${name}\n    ${e.message.split('\n')[0]}`) }
}

// ── fake fetch ────────────────────────────────────────────────────────────
const realFetch = globalThis.fetch
let calls = []
function fakeFetch(handler) {
  calls = []
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init, body: init?.body ? JSON.parse(init.body) : null })
    return handler(url, init)
  }
}
const json = (status, data) => ({ status, ok: status >= 200 && status < 300, json: async () => data })
const backendReply = (code, extra = {}) => json(200, {
  ok: code === 'ok' || code === 'duplicate', code, reference_id: 'SR-ABCDEF12', state: '', duplicate: code === 'duplicate',
  retryable: false, field: '', upstream_code: code, message: 'English server message', ...extra,
})
const ALL_CODES = ['ok', 'duplicate', 'invalid_input', 'session_required', 'session_expired', 'otp_required', 'not_available',
  'rate_limited', 'queue_failed', 'unreachable', 'upstream_error', 'outcome_unknown', 'internal_error']
const GOOD = 'The due date shown by the chatbot is wrong for my return.'
const base = { description: GOOD, category: 'incorrect_answer', referenceId: 'SR-TESTREF001', lang: 'en', aspSession: 'cookie-value' }

// nothing about a report may be logged
const logged = []
for (const k of ['log', 'info', 'warn', 'error', 'debug']) {
  const orig = console[k]
  console[k] = (...a) => { logged.push(a.map(String).join(' ')) ; void orig }
}

// ══ API helper ════════════════════════════════════════════════════════════
say('API helper')
await test('posts to /support-request with exactly the accepted fields', async () => {
  fakeFetch(() => backendReply('ok', { reference_id: 'SR-TESTREF001' }))
  await M.submitSupportRequest(base)
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, 'http://backend.test/support-request')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(Object.keys(calls[0].body).sort(), ['asp_session', 'category', 'description', 'lang', 'reference_id'])
  assert.equal(calls[0].body.asp_session, 'cookie-value')
  assert.equal(calls[0].body.reference_id, 'SR-TESTREF001')
})
await test('Q&A fields are sent only when provided', async () => {
  fakeFetch(() => backendReply('ok'))
  await M.submitSupportRequest(base)
  assert.ok(!('last_query' in calls[0].body) && !('chatbot_answer' in calls[0].body))
  await M.submitSupportRequest({ ...base, lastQuery: 'q', chatbotAnswer: 'a' })
  assert.equal(calls[1].body.last_query, 'q'); assert.equal(calls[1].body.chatbot_answer, 'a')
})
await test('never sends identity fields (login id, user id, recipient)', async () => {
  fakeFetch(() => backendReply('ok'))
  await M.submitSupportRequest({ ...base, loginId: 'x', userId: 'y', to: 'z@example.com', lastQuery: 'q', chatbotAnswer: 'a' })
  const allowed = new Set(['description', 'category', 'reference_id', 'session_ref', 'last_query', 'chatbot_answer', 'asp_session', 'lang'])
  for (const k of Object.keys(calls[0].body)) assert.ok(allowed.has(k), `unexpected field ${k}`)
  assert.ok(!('session_ref' in calls[0].body))
})
await test('omits asp_session when there is none', async () => {
  fakeFetch(() => backendReply('ok'))
  await M.submitSupportRequest({ ...base, aspSession: '' })
  assert.ok(!('asp_session' in calls[0].body))
})
for (const code of ALL_CODES) {
  await test(`maps backend code ${code}`, async () => {
    fakeFetch(() => backendReply(code))
    const r = await M.submitSupportRequest(base)
    assert.equal(r.code, code)
    assert.equal(r.ok, code === 'ok' || code === 'duplicate')
    assert.equal(r.duplicate, code === 'duplicate')
  })
}
await test('keeps the reference id the backend answers with (duplicate = the original)', async () => {
  fakeFetch(() => backendReply('duplicate', { reference_id: 'SR-ORIGINAL01' }))
  assert.equal((await M.submitSupportRequest(base)).referenceId, 'SR-ORIGINAL01')
})
await test('ok:true with a failure code, or a success code with ok:false, is NOT success', async () => {
  fakeFetch(() => backendReply('queue_failed', { ok: true }))
  assert.equal((await M.submitSupportRequest(base)).ok, false)
  fakeFetch(() => backendReply('ok', { ok: false }))
  const r = await M.submitSupportRequest(base)
  assert.equal(r.ok, false); assert.equal(r.code, 'outcome_unknown')
})
await test('unknown or missing code is outcome_unknown, never success', async () => {
  fakeFetch(() => json(200, { ok: true, code: 'brand_new_code' }))
  let r = await M.submitSupportRequest(base)
  assert.equal(r.ok, false); assert.equal(r.code, 'outcome_unknown')
  fakeFetch(() => json(200, { ok: true }))
  r = await M.submitSupportRequest(base)
  assert.equal(r.ok, false); assert.equal(r.code, 'outcome_unknown')
  fakeFetch(() => json(200, null))
  assert.equal((await M.submitSupportRequest(base)).code, 'outcome_unknown')
})
await test('network failure never throws and is outcome_unknown', async () => {
  fakeFetch(() => { throw new TypeError('Failed to fetch') })
  const r = await M.submitSupportRequest(base)
  assert.equal(r.ok, false); assert.equal(r.code, 'outcome_unknown'); assert.equal(r.referenceId, 'SR-TESTREF001')
})
await test('abort/timeout is outcome_unknown', async () => {
  fakeFetch((_u, init) => new Promise((_res, rej) => init.signal.addEventListener('abort', () => rej(new DOMException('aborted', 'AbortError')))))
  const ctl = new AbortController()
  const p = M.submitSupportRequest({ ...base, signal: ctl.signal })
  ctl.abort()
  assert.equal((await p).code, 'outcome_unknown')
})
await test('non-JSON body and 5xx are outcome_unknown', async () => {
  fakeFetch(() => ({ status: 200, ok: true, json: async () => { throw new SyntaxError('bad json') } }))
  assert.equal((await M.submitSupportRequest(base)).code, 'outcome_unknown')
  for (const st of [500, 502, 503, 504]) {
    fakeFetch(() => json(st, { detail: 'boom <stack trace>' }))
    const r = await M.submitSupportRequest(base)
    assert.equal(r.ok, false); assert.equal(r.code, 'outcome_unknown')
  }
})
await test('HTTP 422 is invalid_input and HTTP 429 is rate_limited', async () => {
  fakeFetch(() => json(422, { detail: [{ msg: 'x' }] }))
  assert.equal((await M.submitSupportRequest(base)).code, 'invalid_input')
  fakeFetch(() => json(429, {}))
  assert.equal((await M.submitSupportRequest(base)).code, 'rate_limited')
})
await test('makes one request per call (no automatic retry)', async () => {
  fakeFetch(() => json(500, {}))
  await M.submitSupportRequest(base)
  assert.equal(calls.length, 1)
})
await test('does not log report content or the session cookie', async () => {
  fakeFetch(() => backendReply('ok'))
  await M.submitSupportRequest({ ...base, lastQuery: 'secret question', chatbotAnswer: 'secret answer' })
  fakeFetch(() => { throw new TypeError('offline') })
  await M.submitSupportRequest(base)
  const all = logged.join('\n')
  for (const s of [GOOD, 'cookie-value', 'secret question', 'secret answer']) assert.ok(!all.includes(s))
})

// ══ logic ═════════════════════════════════════════════════════════════════
say('Logic')
await test('description limits: 10..2000 after trimming', () => {
  assert.equal(M.validateDescription('123456789'), 'support.report.err.tooShort')
  assert.equal(M.validateDescription('1234567890'), null)
  assert.equal(M.validateDescription('x'.repeat(2000)), null)
  assert.equal(M.validateDescription('x'.repeat(2001)), 'support.report.err.tooLong')
  assert.equal(M.validateDescription('   abc        '), 'support.report.err.tooShort')
  assert.equal(M.validateDescription(''), 'support.report.err.tooShort')
  assert.equal(M.validateDescription(undefined), 'support.report.err.tooShort')
})
await test('categories are exactly the four accepted values', () => {
  assert.deepEqual(M.CATEGORIES, ['incorrect_answer', 'technical_problem', 'missing_information', 'other'])
})
await test('reference ids match the backend pattern and differ', () => {
  const ids = new Set()
  for (let i = 0; i < 50; i++) { const id = M.newReferenceId(); assert.match(id, /^SR-[A-Z0-9]{6,24}$/); ids.add(id) }
  assert.equal(ids.size, 50)
})
await test('every backend code has a presentation, unknown codes are never success', () => {
  for (const c of ALL_CODES) assert.ok(M.CODE_INFO[c], c)
  assert.equal(M.infoForCode('made_up').kind, 'retry')
  assert.deepEqual(Object.entries(M.CODE_INFO).filter(([, v]) => v.kind === 'success').map(([k]) => k).sort(), ['duplicate', 'ok'])
  assert.deepEqual(['session_required', 'session_expired', 'otp_required'].map((c) => M.CODE_INFO[c].kind), ['auth', 'auth', 'auth'])
})
await test('lastExchange takes only the last question and answer, clipped', () => {
  const msgs = [
    { role: 'user', text: 'old question' }, { role: 'assistant', text: 'old answer' },
    { role: 'user', text: 'q'.repeat(900) }, { role: 'feedback_prompt' },
    { role: 'assistant', text: 'ignored', textEn: 'a'.repeat(1500) }, { role: 'feedback_negative' },
  ]
  const r = M.lastExchange(msgs)
  assert.equal(r.lastQuery.length, 500); assert.equal(r.chatbotAnswer.length, 1000)
  assert.ok(!r.lastQuery.includes('old') && !r.chatbotAnswer.includes('ignored'))
  assert.deepEqual(M.lastExchange([]), { lastQuery: '', chatbotAnswer: '' })
})

// ══ controller (submit lifecycle) ═════════════════════════════════════════
say('Controller')
const mkSubmit = (...replies) => {
  const seen = []
  const fn = async (args) => { seen.push(args); const r = replies.length > 1 ? replies.shift() : replies[0]; return typeof r === 'function' ? r(args) : r }
  fn.seen = seen
  return fn
}
const res = (code, extra = {}) => ({ ok: code === 'ok' || code === 'duplicate', code, referenceId: 'SR-X', duplicate: code === 'duplicate', retryable: false, field: '', ...extra })
const form = (o = {}) => ({ description: GOOD, category: 'other', includeQa: false, lang: 'en', aspSession: 'cookie', getMessages: () => [], ...o })

await test('invalid description does not call the API', async () => {
  const s = mkSubmit(res('ok')); const c = M.createSupportReport({ submit: s })
  await c.submit(form({ description: 'short' }))
  assert.equal(s.seen.length, 0); assert.equal(c.getState().status, 'idle')
})
await test('shows loading, then success', async () => {
  let release; const gate = new Promise((r) => { release = r })
  const s = mkSubmit(() => gate.then(() => res('ok'))); const c = M.createSupportReport({ submit: s })
  const p = c.submit(form())
  assert.equal(c.getState().status, 'sending')
  release(); await p
  assert.equal(c.getState().status, 'done'); assert.equal(c.getState().result.code, 'ok')
})
await test('double click sends one request', async () => {
  let release; const gate = new Promise((r) => { release = r })
  const s = mkSubmit(() => gate.then(() => res('ok'))); const c = M.createSupportReport({ submit: s })
  const p1 = c.submit(form()); const p2 = c.submit(form()); const p3 = c.submit(form())
  release(); await Promise.all([p1, p2, p3])
  assert.equal(s.seen.length, 1)
})
await test('no further submit after success', async () => {
  const s = mkSubmit(res('ok')); const c = M.createSupportReport({ submit: s })
  await c.submit(form()); await c.submit(form())
  assert.equal(s.seen.length, 1)
})
await test('retry reuses the SAME reference id after every failure type', async () => {
  for (const code of ['outcome_unknown', 'unreachable', 'queue_failed', 'rate_limited', 'internal_error', 'session_expired']) {
    const s = mkSubmit(res(code), res(code), res('ok')); const c = M.createSupportReport({ submit: s })
    await c.submit(form()); assert.equal(c.getState().status, 'failed', code)
    await c.submit(form()); await c.submit(form())
    assert.equal(s.seen.length, 3)
    assert.deepEqual([...new Set(s.seen.map((a) => a.referenceId))], [c.referenceId], code)
    assert.match(c.referenceId, /^SR-[A-Z0-9]{6,24}$/)
  }
})
await test('a new report gets a new reference id', () => {
  assert.notEqual(M.createSupportReport({ submit: mkSubmit(res('ok')) }).referenceId, M.createSupportReport({ submit: mkSubmit(res('ok')) }).referenceId)
})
await test('no automatic retry after a failure', async () => {
  const s = mkSubmit(res('outcome_unknown')); const c = M.createSupportReport({ submit: s })
  await c.submit(form()); await new Promise((r) => setTimeout(r, 30))
  assert.equal(s.seen.length, 1)
})
await test('duplicate is treated as accepted', async () => {
  const c = M.createSupportReport({ submit: mkSubmit(res('duplicate')) })
  await c.submit(form()); assert.equal(c.getState().status, 'done')
})
await test('a throwing submit becomes an unconfirmed failure, not success', async () => {
  const c = M.createSupportReport({ submit: async () => { throw new Error('boom') } })
  await c.submit(form())
  assert.equal(c.getState().status, 'failed'); assert.equal(c.getState().result.code, 'outcome_unknown')
})
await test('question/answer are NOT read or sent unless the box is ticked', async () => {
  let read = 0
  const getMessages = () => { read++; return [{ role: 'user', text: 'q' }, { role: 'assistant', text: 'a' }] }
  const s = mkSubmit(res('ok')); const c = M.createSupportReport({ submit: s })
  await c.submit(form({ getMessages }))
  assert.equal(read, 0); assert.equal(s.seen[0].lastQuery, undefined); assert.equal(s.seen[0].chatbotAnswer, undefined)
})
await test('question/answer are sent when the box is ticked, and only the last pair', async () => {
  const getMessages = () => [{ role: 'user', text: 'first' }, { role: 'assistant', text: 'first a' }, { role: 'user', text: 'last q' }, { role: 'assistant', text: 'last a' }]
  const s = mkSubmit(res('ok')); const c = M.createSupportReport({ submit: s })
  await c.submit(form({ includeQa: true, getMessages }))
  assert.equal(s.seen[0].lastQuery, 'last q'); assert.equal(s.seen[0].chatbotAnswer, 'last a')
})
await test('end to end with the real API helper: opt-out payload and retry reuse', async () => {
  let n = 0
  fakeFetch(() => (++n === 1 ? json(503, {}) : backendReply('ok')))
  const c = M.createSupportReport({ submit: M.submitSupportRequest })
  await c.submit(form()); assert.equal(c.getState().result.code, 'outcome_unknown')
  await c.submit(form()); assert.equal(c.getState().status, 'done')
  assert.equal(calls.length, 2)
  assert.equal(calls[0].body.reference_id, calls[1].body.reference_id)
  assert.ok(!('last_query' in calls[0].body) && !('chatbot_answer' in calls[0].body))
  assert.equal(calls[0].body.asp_session, 'cookie')
})

// ══ rendering ═════════════════════════════════════════════════════════════
say('Rendering')
const h = React.createElement
const render = (lang, el) => renderToStaticMarkup(h(LanguageContext.Provider, { value: lang }, el))
const text = (html) => html.replace(/<[^>]+>/g, ' ').replace(/&#x27;/g, "'").replace(/&amp;/g, '&').replace(/\s+/g, ' ')
const withState = async (replies, doSubmit = true, never = false) => {
  const c = M.createSupportReport({ submit: never ? () => new Promise(() => {}) : mkSubmit(replies) })
  if (doSubmit) { const p = c.submit(form()); if (!never) await p }
  return c
}
const LANGS = ['en', 'fr', 'ar', 'hi']

await test('offer shows Report an issue / No thanks and no hard-coded addresses', () => {
  const html = render('en', h(M.SupportReportOffer))
  assert.match(html, /Report an issue/); assert.match(html, /No thanks/)
  assert.ok(!/mailto:|@[a-z0-9-]+\.[a-z]/i.test(html), 'static email address rendered')
})
await test('form (idle): categories, description, counter, unchecked checkbox, Cancel, Submit', () => {
  const html = render('en', h(M.SupportReportForm, { controller: M.createSupportReport({ submit: mkSubmit(res('ok')) }) }))
  for (const label of ['Incorrect answer', 'Technical problem', 'Missing information', 'Other', 'Include my last question and answer', 'Cancel', 'Submit', '0 / 2000']) {
    assert.ok(text(html).includes(label), label)
  }
  assert.match(html, /<input type="checkbox"(?![^>]*checked)/)
  for (const v of M.CATEGORIES) assert.ok(html.includes(`value="${v}"`), v)
})
await test('form is the inline offer default category: incorrect answer pre-selected', () => {
  const html = render('en', h(M.SupportReportForm, { defaultCategory: 'incorrect_answer', controller: M.createSupportReport({ submit: mkSubmit(res('ok')) }) }))
  assert.match(html, /<option value="incorrect_answer" selected/)
})
await test('loading state disables Submit, Cancel and inputs', async () => {
  const html = render('en', h(M.SupportReportForm, { controller: await withState(null, true, true) }))
  assert.match(html, /<button type="submit"[^>]*disabled/)
  assert.match(html, /<textarea[^>]*disabled/)
  assert.ok(text(html).includes('Submitting'))
})
await test('success shows exactly the required message and the reference, never "delivered"', async () => {
  const html = render('en', h(M.SupportReportForm, { controller: await withState(res('ok', { referenceId: 'SR-ABC12345' })) }))
  assert.ok(text(html).includes('Your report was submitted to the support queue.'))
  assert.ok(text(html).includes('SR-ABC12345'))
  assert.ok(!/deliver|received|email was sent|emailed/i.test(text(html)))
})
await test('duplicate says the existing report was already accepted', async () => {
  const html = render('en', h(M.SupportReportForm, { controller: await withState(res('duplicate')) }))
  assert.ok(/already accepted/.test(text(html)))
})
const NON_SUCCESS = ALL_CODES.filter((c) => c !== 'ok' && c !== 'duplicate')
for (const code of NON_SUCCESS) {
  await test(`failure ${code}: translated message in an alert, no success wording`, async () => {
    for (const lang of LANGS) {
      const t = makeT(lang)
      const html = render(lang, h(M.SupportReportForm, { controller: await withState(res(code)) }))
      assert.ok(text(html).includes(t(`support.report.code.${code}`)), `${lang}`)
      assert.match(html, /role="alert"/)
      assert.ok(!html.includes(t('support.report.code.ok')))
      assert.ok(!html.includes('undefined'))
    }
  })
}
await test('retryable failures offer Try again; message semantics are right', async () => {
  const en = makeT('en')
  for (const code of ['outcome_unknown', 'unreachable', 'queue_failed', 'rate_limited', 'internal_error', 'upstream_error']) {
    assert.ok(text(render('en', h(M.SupportReportForm, { controller: await withState(res(code)) }))).includes('Try again'), code)
  }
  assert.ok(!text(render('en', h(M.SupportReportForm, { controller: await withState(res('not_available')) }))).includes('Try again'))
  assert.ok(/currently unavailable/.test(en('support.report.code.not_available')))
  // honest wording: "nothing was sent" is never claimed, and unconfirmed outcomes keep the reference ID
  for (const c of ALL_CODES) assert.ok(!/nothing was sent/i.test(en(`support.report.code.${c}`)), c)
  for (const c of ['queue_failed', 'upstream_error', 'outcome_unknown', 'internal_error']) assert.ok(/same reference ID/.test(en(`support.report.code.${c}`)), c)
  assert.ok(/may or may not have been received/.test(en('support.report.code.outcome_unknown')))
  assert.ok(!/not queued twice|so it is not/.test(en('support.report.code.outcome_unknown')))
  assert.ok(/wait/.test(en('support.report.code.rate_limited')))
  assert.ok(/could not confirm/.test(en('support.report.code.outcome_unknown')) && /same reference ID/.test(en('support.report.code.outcome_unknown')))
  for (const c of ['session_expired', 'otp_required', 'session_required']) assert.ok(/sign in|OTP/.test(en(`support.report.code.${c}`)), c)
})
await test('every UI string exists and is translated in en/fr/ar/hi', () => {
  const keys = new Set(['support.report.open', 'support.report.decline', 'support.report.title', 'support.report.category', 'support.report.description',
    'support.report.placeholder', 'support.report.err.tooShort', 'support.report.err.tooLong', 'support.report.includeQa', 'support.report.includeQaHint',
    'support.report.sending', 'support.report.retry', 'support.report.reference', 'common.cancel', 'common.submit', 'common.close', 'support.sorry',
    ...M.CATEGORIES.map((c) => `support.report.cat.${c}`), ...ALL_CODES.map((c) => `support.report.code.${c}`)])
  const en = makeT('en')
  for (const k of keys) {
    const base = en(k)
    assert.ok(base && base !== k && !base.includes('undefined'), `en ${k}`)
    for (const lang of ['fr', 'ar', 'hi']) {
      const v = makeT(lang)(k)
      assert.ok(v && v !== k, `${lang} ${k}`)
      if (!['support.report.cat.other'].includes(k) || lang !== 'fr') { /* "Date"-style identical words are allowed only where the word is the same */ }
      if (lang === 'ar') assert.match(v, /[؀-ۿ]/, `ar ${k}`)
      if (lang === 'hi') assert.match(v, /[ऀ-ॿ]/, `hi ${k}`)
    }
  }
})
await test('fr/ar/hi rendering contains none of the English UI wording', async () => {
  const english = ['Report an issue', 'No thanks', 'Category', 'Describe the problem', 'Include my last question', 'Cancel', 'Submit', 'Incorrect answer',
    'Technical problem', 'Missing information', 'Try again', 'Reference ID', 'could not confirm', 'unexpected answer']
  for (const lang of ['fr', 'ar', 'hi']) {
    const forms = [
      render(lang, h(M.SupportReportOffer)),
      render(lang, h(M.SupportReportForm, { controller: M.createSupportReport({ submit: mkSubmit(res('ok')) }) })),
      render(lang, h(M.SupportReportForm, { controller: await withState(res('outcome_unknown')) })),
      render(lang, h(M.SupportReportForm, { controller: await withState(res('ok')) })),
    ]
    for (const html of forms) for (const w of english) assert.ok(!text(html).includes(w), `${lang}: "${w}"`)
  }
})
await test('Arabic is right-to-left and both stylesheets carry narrow-screen and RTL rules', () => {
  assert.equal(isRtl('ar'), true); assert.equal(isRtl('fr'), false)
  for (const f of ['App.5.5.css', 'App.6.0.css']) {
    const css = readFileSync(join(root, 'src', f), 'utf8')
    assert.ok(css.includes('.support-report {') && css.includes('.support-report-link'), f)
    assert.ok(css.includes('[dir="rtl"] .support-report-actions'), `${f} rtl`)
    assert.ok(/@media \(max-width: 480px\)\s*\{\s*\.support-report/.test(css), `${f} narrow`)
  }
})

// ══ wiring (existing behaviour intact) ════════════════════════════════════
say('Wiring')
const src = (p) => readFileSync(join(root, 'src', p), 'utf8')
await test('thumbs up/down are unchanged and still call onFeedback', () => {
  const mb = src('components/MessageBubble.jsx')
  assert.ok(mb.includes("onClick={() => handleClick('yes')}") && mb.includes("onClick={() => handleClick('no')}"))
  assert.ok(mb.includes('feedback-yes') && mb.includes('feedback-no'))
  assert.ok(mb.includes("onFeedback?.(response, { query, intent, resultType })"))
  const app = src('App.jsx')
  assert.ok(app.includes("{ role: 'feedback_positive' }") && app.includes("{ role: 'feedback_negative' }"))
  assert.ok(app.includes("sendFeedback(response === 'yes' ? 'up' : 'down'"))
})
await test('negative rating now offers the report form; no static email links remain', () => {
  const mb = src('components/MessageBubble.jsx')
  assert.ok(mb.includes("if (role === 'feedback_negative') return <SupportReportOffer />"))
  for (const f of ['components/MessageBubble.jsx', 'components/SupportReport.jsx', 'App.jsx']) {
    assert.ok(!/mailto:|support@company\.com|chatbot-support@company\.com/.test(src(f)), f)
  }
})
await test('persistent entry exists in the footer and the report never enters the message history', () => {
  const app = src('App.jsx')
  assert.ok(app.includes('support-report-link') && app.includes('<SupportReportForm'))
  const after = app.slice(app.indexOf('const [supportOpen'))
  // the support form is opened/closed with its own state, never by pushing into `messages`
  assert.ok(!/setMessages\([^)]*support/i.test(after))
  assert.ok(!/support/i.test(app.slice(app.indexOf('_idbSaveHistory('), app.indexOf('_idbSaveHistory(') + 200)))
})

// ── summary ───────────────────────────────────────────────────────────────
globalThis.fetch = realFetch
say(`\n${passed} passed, ${failures.length} failed`)
if (failures.length) { for (const [n, e] of failures) say(`\n--- ${n}\n${e.stack}`); process.exit(1) }
