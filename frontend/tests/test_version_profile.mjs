// Run: node --test frontend/tests/test_version_profile.mjs
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  applyProfileToEnv, parseEnvText, readSelectedVersion, resolveVersionProfile, withBackendPort,
} from '../version-profile.mjs'

const REAL_FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** A throw-away repo: <tmp>/.env and <tmp>/frontend/profiles/<v>.env */
function fakeRepo({ rootEnv = null, profiles = {} } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'verprof-'))
  const frontend = path.join(root, 'frontend')
  fs.mkdirSync(path.join(frontend, 'profiles'), { recursive: true })
  if (rootEnv !== null) fs.writeFileSync(path.join(root, '.env'), rootEnv)
  for (const [v, text] of Object.entries(profiles)) fs.writeFileSync(path.join(frontend, 'profiles', `${v}.env`), text)
  return { root, frontend }
}

const P55 = 'VITE_API_BASE_URL_DEV=http://127.0.0.1:8001\nVITE_API_BASE_URL_PROD=/AIChatBot/api\nVITE_BASE_PATH=/AiChatbot/\nBACKEND_PORT=8001\n'
const P60 = 'VITE_API_BASE_URL_DEV=http://127.0.0.1:8002\nVITE_API_BASE_URL_PROD=/AiChatBot6.0/api\nVITE_BASE_PATH=/AiChatBot6.0/\nBACKEND_PORT=8002\n'

test('parseEnvText ignores comments and blanks and strips quotes', () => {
  assert.deepEqual(parseEnvText('# c\n\nA=1\nB = "two"\nC=\'3\'\nbad line\n'), { A: '1', B: 'two', C: '3' })
})

test('version comes from the root .env', () => {
  const { root } = fakeRepo({ rootEnv: 'FOO=1\nAPP_VERSION=6.0\n' })
  assert.equal(readSelectedVersion({ rootDir: root, env: {} }), '6.0')
})

test('APP_VERSION in the environment wins over the root .env', () => {
  const { root } = fakeRepo({ rootEnv: 'APP_VERSION=5.5\n' })
  assert.equal(readSelectedVersion({ rootDir: root, env: { APP_VERSION: '6.0' } }), '6.0')
})

test('ENV_FILE names the file the version is read from', () => {
  const { root } = fakeRepo({ rootEnv: 'APP_VERSION=5.5\n' })
  fs.writeFileSync(path.join(root, '.env.six'), 'APP_VERSION=6.0\n')
  assert.equal(readSelectedVersion({ rootDir: root, env: { ENV_FILE: '.env.six' } }), '6.0')
})

test('no APP_VERSION anywhere -> no profile (old behaviour)', () => {
  const { frontend } = fakeRepo({ rootEnv: 'FOO=1\n', profiles: { '5.5': P55 } })
  assert.equal(resolveVersionProfile({ frontendDir: frontend, mode: 'production', env: {} }), null)
})

test('missing root .env -> no profile', () => {
  const { frontend } = fakeRepo({ profiles: { '5.5': P55 } })
  assert.equal(resolveVersionProfile({ frontendDir: frontend, mode: 'development', env: {} }), null)
})

test('5.5 and 6.0 resolve to their own values, per mode', () => {
  for (const [v, text, devApi, prodApi, base, port] of [
    ['5.5', P55, 'http://127.0.0.1:8001', '/AIChatBot/api', '/AiChatbot/', 8001],
    ['6.0', P60, 'http://127.0.0.1:8002', '/AiChatBot6.0/api', '/AiChatBot6.0/', 8002],
  ]) {
    const { frontend } = fakeRepo({ rootEnv: `APP_VERSION=${v}\n`, profiles: { '5.5': P55, '6.0': P60 } })
    const dev = resolveVersionProfile({ frontendDir: frontend, mode: 'development', env: {} })
    const prod = resolveVersionProfile({ frontendDir: frontend, mode: 'production', env: {} })
    assert.equal(dev.version, v)
    assert.equal(dev.vite.VITE_API_BASE_URL, devApi)
    assert.equal(prod.vite.VITE_API_BASE_URL, prodApi)
    assert.equal(prod.vite.VITE_BASE_PATH, base)
    assert.equal(prod.backendPort, port)
    assert.ok(text.includes(String(port)))
  }
})

test('switching only APP_VERSION switches every value', () => {
  const a = fakeRepo({ rootEnv: 'APP_VERSION=5.5\n', profiles: { '5.5': P55, '6.0': P60 } })
  const b = fakeRepo({ rootEnv: 'APP_VERSION=6.0\n', profiles: { '5.5': P55, '6.0': P60 } })
  const p55 = resolveVersionProfile({ frontendDir: a.frontend, mode: 'production', env: {} })
  const p60 = resolveVersionProfile({ frontendDir: b.frontend, mode: 'production', env: {} })
  for (const key of ['VITE_API_BASE_URL', 'VITE_BASE_PATH']) assert.notEqual(p55.vite[key], p60.vite[key])
  assert.notEqual(p55.backendPort, p60.backendPort)
})

test('a version without a profile fails with a message naming the file', () => {
  const { frontend } = fakeRepo({ rootEnv: 'APP_VERSION=7.0\n', profiles: { '5.5': P55 } })
  assert.throws(
    () => resolveVersionProfile({ frontendDir: frontend, mode: 'production', env: {} }),
    /APP_VERSION=7\.0 has no frontend profile .*7\.0\.env.*Known versions: 5\.5/,
  )
})

test('applyProfileToEnv fills missing keys but never overrides an exported variable', () => {
  const env = { VITE_API_BASE_URL: 'http://exported:1' }
  const set = applyProfileToEnv({ vite: { VITE_API_BASE_URL: '/from-profile', VITE_BASE_PATH: '/b/' } }, env)
  assert.equal(env.VITE_API_BASE_URL, 'http://exported:1')
  assert.equal(env.VITE_BASE_PATH, '/b/')
  assert.deepEqual(set, ['VITE_BASE_PATH'])
  assert.deepEqual(applyProfileToEnv(null, {}), [])
})

test('withBackendPort changes only the rewrite port', () => {
  const xml = '<action type="Rewrite"\n url="http://127.0.0.1:8002/{R:1}" appendQueryString="true" />\n<x a="http://127.0.0.1:9999/y"/>'
  const out = withBackendPort(xml, 8001)
  assert.ok(out.includes('url="http://127.0.0.1:8001/{R:1}"'))
  assert.ok(out.includes('http://127.0.0.1:9999/y'))       // unrelated URL untouched
  assert.equal(withBackendPort(xml, null), xml)
})

test('the shipped profiles are complete and self-consistent', () => {
  for (const v of ['5.5', '6.0']) {
    const p = parseEnvText(fs.readFileSync(path.join(REAL_FRONTEND, 'profiles', `${v}.env`), 'utf8'))
    for (const key of ['VITE_API_BASE_URL_DEV', 'VITE_API_BASE_URL_PROD', 'VITE_BASE_PATH', 'BACKEND_PORT']) {
      assert.ok(p[key], `${v}.env is missing ${key}`)
    }
    assert.ok(p.VITE_BASE_PATH.startsWith('/') && p.VITE_BASE_PATH.endsWith('/'))
    assert.ok(p.VITE_API_BASE_URL_DEV.endsWith(`:${p.BACKEND_PORT}`), `${v}: dev API port must equal BACKEND_PORT`)
  }
  const a = parseEnvText(fs.readFileSync(path.join(REAL_FRONTEND, 'profiles', '5.5.env'), 'utf8'))
  const b = parseEnvText(fs.readFileSync(path.join(REAL_FRONTEND, 'profiles', '6.0.env'), 'utf8'))
  assert.notEqual(a.BACKEND_PORT, b.BACKEND_PORT)
  assert.notEqual(a.VITE_BASE_PATH, b.VITE_BASE_PATH)
})

test('the real repo: the version selected in the root .env resolves', () => {
  const rootEnv = fs.existsSync(path.join(REAL_FRONTEND, '..', '.env'))
  const p = resolveVersionProfile({ frontendDir: REAL_FRONTEND, mode: 'production', env: rootEnv ? {} : { APP_VERSION: '5.5' } })
  assert.ok(p && ['5.5', '6.0'].includes(p.version))
})
