// frontend/version-profile.mjs
//
// APP_VERSION (5.5 or 6.0) is the single switch for everything that differs
// between the two builds of this frontend. It is read from the repo's root .env
// - the same line the backend reads - or from the APP_VERSION environment
// variable, which wins. The settings for that version live in
// frontend/profiles/<version>.env.
//
// Why this is a separate module: vite.config.js needs the answer BEFORE Vite
// resolves its own environment, and Vite only loads files named .env*, so the
// profile is read here and handed to Vite through process.env (Vite gives real
// VITE_* environment variables priority over .env.* files).
//
// If no APP_VERSION is found anywhere, nothing is applied and the build behaves
// exactly as it did before profiles existed (frontend/.env.development and
// frontend/.env.production alone).

import fs from 'node:fs'
import path from 'node:path'

/** KEY=VALUE lines -> object. # comments and blank lines ignored, quotes stripped. */
export function parseEnvText(text) {
  const out = {}
  for (const raw of String(text).split(/\r?\n/)) {
    const line = raw.trim()
    if (!line || line.startsWith('#')) continue
    const eq = line.indexOf('=')
    if (eq < 1) continue
    const key = line.slice(0, eq).trim()
    let value = line.slice(eq + 1).trim()
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1)
    }
    out[key] = value
  }
  return out
}

function readEnvFile(file) {
  try {
    return parseEnvText(fs.readFileSync(file, 'utf8'))
  } catch {
    return {}
  }
}

/** The selected version: APP_VERSION env var, else the repo root .env (or ENV_FILE). null if unset. */
export function readSelectedVersion({ rootDir, env = process.env }) {
  const fromEnv = (env.APP_VERSION || '').trim()
  if (fromEnv) return fromEnv
  const explicit = (env.ENV_FILE || '').trim()
  const file = explicit ? path.resolve(rootDir, explicit) : path.join(rootDir, '.env')
  return (readEnvFile(file).APP_VERSION || '').trim() || null
}

/**
 * The profile for the selected version, or null when no version is selected.
 * Throws with a readable message for a version that has no profile file.
 *
 * `vite` holds the VITE_* values to hand to Vite for this mode:
 *   - build (mode "production") uses the *_PROD keys, anything else the *_DEV keys
 *   - VITE_BASE_PATH applies to both
 * `backendPort` is what dist/web.config must forward to.
 */
export function resolveVersionProfile({ frontendDir, mode, env = process.env }) {
  const rootDir = path.resolve(frontendDir, '..')
  const version = readSelectedVersion({ rootDir, env })
  if (!version) return null

  const profileFile = path.join(frontendDir, 'profiles', `${version}.env`)
  if (!fs.existsSync(profileFile)) {
    const known = fs.existsSync(path.join(frontendDir, 'profiles'))
      ? fs.readdirSync(path.join(frontendDir, 'profiles')).filter((f) => f.endsWith('.env')).map((f) => f.replace(/\.env$/, ''))
      : []
    throw new Error(
      `APP_VERSION=${version} has no frontend profile (expected ${profileFile}). Known versions: ${known.join(', ') || 'none'}.`,
    )
  }

  const p = readEnvFile(profileFile)
  const suffix = mode === 'production' ? 'PROD' : 'DEV'
  const vite = {}
  const apiBase = p[`VITE_API_BASE_URL_${suffix}`]
  const trusted = p[`VITE_TRUSTED_PARENT_ORIGINS_${suffix}`]
  if (apiBase !== undefined) vite.VITE_API_BASE_URL = apiBase
  if (trusted !== undefined) vite.VITE_TRUSTED_PARENT_ORIGINS = trusted
  if (p.VITE_BASE_PATH !== undefined) vite.VITE_BASE_PATH = p.VITE_BASE_PATH

  const backendPort = p.BACKEND_PORT ? Number.parseInt(p.BACKEND_PORT, 10) : null
  return { version, profileFile, vite, backendPort: Number.isFinite(backendPort) ? backendPort : null }
}

/**
 * Put the profile's VITE_* values into process.env without overriding anything the
 * caller exported themselves. Returns the keys that were set.
 */
export function applyProfileToEnv(profile, env = process.env) {
  const set = []
  if (!profile) return set
  for (const [key, value] of Object.entries(profile.vite)) {
    if (env[key] !== undefined && env[key] !== '') continue   // an exported variable wins
    env[key] = value
    set.push(key)
  }
  return set
}

/** web.config text with its reverse-proxy rewrite pointed at `port` (nothing else changed). */
export function withBackendPort(webConfigText, port) {
  if (!port) return webConfigText
  return webConfigText.replace(/(url=["']https?:\/\/[^/:"']+:)\d+(\/\{R:1\})/i, `$1${port}$2`)
}

/** Vite plugin: after a build, make dist/web.config and dist/version.txt match the selected version. */
export function versionBuildPlugin(profile) {
  let outDir = ''
  return {
    name: 'version-build-files',
    apply: 'build',
    configResolved(config) {
      outDir = path.resolve(config.root, config.build.outDir)
    },
    closeBundle() {
      if (!profile || !outDir) return
      const webConfig = path.join(outDir, 'web.config')
      if (fs.existsSync(webConfig)) {
        const text = fs.readFileSync(webConfig, 'utf8')
        const next = withBackendPort(text, profile.backendPort)
        if (next !== text) fs.writeFileSync(webConfig, next)
      }
      const lines = [
        `version=${profile.version}`,
        `base=${profile.vite.VITE_BASE_PATH ?? ''}`,
        `api=${profile.vite.VITE_API_BASE_URL ?? ''}`,
        `backend_port=${profile.backendPort ?? ''}`,
      ]
      fs.writeFileSync(path.join(outDir, 'version.txt'), lines.join('\n') + '\n')
    },
  }
}
