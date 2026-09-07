// Bundle the app with esbuild and EXECUTE every module body.
//
// `vite build` only proves the syntax parses. A t() call at MODULE level parses
// perfectly and throws ReferenceError at import time, blanking the whole app --
// which is exactly what shipped once. Running the module bodies catches it.
//
//   node scripts/smoke-execute.mjs
import { build } from 'esbuild'
import { pathToFileURL } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..')
process.chdir(ROOT)

// Minimal browser globals so module bodies can run outside a browser.
const store = {}
const g = (name, value) => Object.defineProperty(globalThis, name, { value, configurable: true, writable: true })
g('localStorage', { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v) }, removeItem: k => { delete store[k] } })
g('sessionStorage', globalThis.localStorage)
const el = () => ({ id: '', textContent: '', style: {}, setAttribute() {}, appendChild() {}, addEventListener() {}, classList: { add() {}, remove() {} } })
g('document', { createElement: el, getElementById: () => null, head: { appendChild() {} }, body: { appendChild() {} }, addEventListener() {}, querySelector: () => null })
g('window', { location: { search: '', href: 'http://localhost/' }, addEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }), localStorage: globalThis.localStorage })
g('navigator', { mediaDevices: {} })

const OUT = '_smoke_bundle.mjs'
let bundled = false
try {
  const out = await build({
    entryPoints: ['src/App.jsx'], bundle: true, write: false, format: 'esm',
    jsx: 'transform', jsxFactory: 'h', jsxFragment: 'F',
    platform: 'neutral', logLevel: 'silent', loader: { '.css': 'empty' },
    external: ['react', 'react-dom', 'react-markdown', 'recharts', 'uuid'],
    define: { 'import.meta.env.VITE_API_BASE_URL': '""' },
  })
  fs.writeFileSync(OUT, out.outputFiles[0].text)
  bundled = true
} catch (e) {
  console.log('BUILD FAILED:')
  for (const m of (e.errors || [])) console.log('  ', m.text, m.location && (m.location.file + ':' + m.location.line))
  process.exit(1)
}
try {
  await import(pathToFileURL(path.join(ROOT, OUT)).href)
  console.log('MODULE EXECUTION: OK - every module body ran without error')
} catch (e) {
  console.log('MODULE EXECUTION FAILED:', e.constructor.name + ':', e.message)
  if (e.stack) console.log(e.stack.split('\n').slice(0, 4).join('\n'))
  process.exitCode = 1
} finally { if (bundled) fs.unlinkSync(OUT) }
