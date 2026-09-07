// Prove that the FRONTEND actually puts `lang` in the request body.
//
// The AI Analysis shipped in English for exactly this reason: the backend
// handled `lang` correctly, the boundary was tested directly, and every unit
// test passed -- while api.js never sent the field. Testing translate_outbound()
// could not catch that, because the gap was on the wire.
//
// This stubs fetch, calls the real exported functions, and inspects the JSON
// that would have gone over the network.
//
//   node scripts/check-lang-propagation.mjs
import { pathToFileURL } from 'node:url'
import path from 'node:path'

const ROOT = path.resolve(
  path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
process.chdir(ROOT)

const g = (name, value) =>
  Object.defineProperty(globalThis, name, { value, configurable: true, writable: true })
g('window', { location: { search: '', href: 'http://localhost/' } })

const sent = []
g('fetch', async (url, init) => {
  // /speech-to-text posts multipart, not JSON -- read both shapes so one
  // stub covers every endpoint.
  const raw = init?.body
  const body = (raw && typeof raw.get === 'function')
    ? Object.fromEntries([...raw.entries()].map(([k, v]) =>
        [k, typeof v === 'string' ? v : '<blob>']))
    : JSON.parse(raw ?? '{}')
  sent.push({ url: String(url), body })
  return {
    ok: true,
    json: async () => ({ llm_summary: 'x', actions: [], response_text: '' }),
  }
})

// api.js uses import.meta.env, which only exists under Vite -- bundle it with
// esbuild first, exactly as the app does.
import { build } from 'esbuild'
import fs from 'node:fs'
const OUT = '_api_probe.mjs'
const built = await build({
  entryPoints: ['src/services/api.js'], bundle: true, write: false, format: 'esm',
  platform: 'neutral', logLevel: 'silent',
  define: { 'import.meta.env.VITE_API_BASE_URL': '""' },
})
fs.writeFileSync(OUT, built.outputFiles[0].text)
const api = await import(pathToFileURL(path.join(ROOT, OUT)).href)
fs.unlinkSync(OUT)

const CASES = [
  ['/compare-execute', (lang) => api.compareInstances('s1', 0, 1, { lang })],
  ['/compare-summary', (lang) => api.fetchCompareSummary([], 'A', 'B', 'RAQ(Monthly)', { lang })],
  ['/explain-category', (lang) => api.explainErrorCategory('f.xml', 'formula_error', null, null, { lang })],
  ['/chat', (lang) => api.sendMessage('hello', 's1', null, null, null, null, [], { lang })],
  ['/guided', (lang) => api.sendGuidedMessage('__GUIDED_START__', 's1', null, null, null, null, { lang })],
]

// Speech-to-text is checked separately: it is multipart, and unlike every
// other endpoint it MUST send 'en' explicitly. Whisper has to be told which
// language is being spoken -- there is no English default to leave alone.
const STT_CASES = ['en', 'fr', 'ar', 'hi']

let failures = 0
for (const [endpoint, call] of CASES) {
  for (const lang of ['en', 'fr', 'ar', 'hi']) {
    sent.length = 0
    try { await call(lang) } catch { /* the stub always resolves */ }
    const req = sent.find((r) => r.url.includes(endpoint))
    if (!req) { console.log(`FAIL ${endpoint} [${lang}]: no request issued`); failures++; continue }
    const got = req.body.lang
    // 'en' must send NOTHING, so the English path stays byte-identical.
    const want = lang === 'en' ? undefined : lang
    const ok = got === want
    if (!ok) failures++
    console.log(`${ok ? 'OK  ' : 'FAIL'} ${endpoint.padEnd(18)} lang=${lang}  body.lang=${JSON.stringify(got)}`)
  }
}

for (const lang of STT_CASES) {
  sent.length = 0
  const blob = new Blob([new Uint8Array([1, 2, 3])], { type: 'audio/webm' })
  try { await api.transcribeAudio(blob, { lang }) } catch { /* stub resolves */ }
  const req = sent.find((r) => r.url.includes('/speech-to-text'))
  const got = req?.body?.lang
  const ok = got === lang        // 'en' included, deliberately
  if (!ok) failures++
  console.log(`${ok ? 'OK  ' : 'FAIL'} ${'/speech-to-text'.padEnd(18)} lang=${lang}  form.lang=${JSON.stringify(got)}`)
}

console.log(failures === 0
  ? '\nLANG PROPAGATION: OK - every endpoint receives the selected language'
  : `\nLANG PROPAGATION: ${failures} FAILURE(S)`)
process.exitCode = failures === 0 ? 0 : 1
