import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { applyProfileToEnv, resolveVersionProfile, versionBuildPlugin } from './version-profile.mjs'

// Dev-proxy target: derived from VITE_API_BASE_URL (frontend/.env.development)
// instead of a port hardcoded here -- one value to change per deployment,
// matching the backend's own single-source-of-truth BACKEND_PORT in .env.
export default defineConfig(({ mode }) => {
  // APP_VERSION (root .env, or the APP_VERSION environment variable) selects
  // frontend/profiles/<version>.env, whose VITE_* values are handed to Vite
  // through process.env BEFORE it resolves its own env: Vite gives real
  // VITE_* variables priority over .env.* files, so the profile wins over
  // .env.development / .env.production without those files being edited, and a
  // variable exported in the shell still wins over the profile. With no
  // APP_VERSION anywhere this does nothing and the build is as it always was.
  const frontendDir = fileURLToPath(new URL('.', import.meta.url))
  const profile = resolveVersionProfile({ frontendDir, mode })
  const applied = applyProfileToEnv(profile)
  if (profile) {
    console.log(`[version] APP_VERSION=${profile.version} -> ${profile.profileFile} (${applied.length ? applied.join(', ') : 'nothing overridden'})`)
  }

  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

  // L-19: the deployment base path (IIS virtual directory the built app is
  // served under) used to be a hardcoded literal here, requiring a source
  // edit + rebuild to switch between a 5.5-style and 6.0-style deployment
  // path. VITE_BASE_PATH (set per environment in .env.development/
  // .env.production, same convention as VITE_API_BASE_URL) makes this a
  // config change instead. Defaults to this app's current deployed path so
  // behavior is unchanged for any environment that doesn't set it.
  const basePath = env.VITE_BASE_PATH || '/AiChatbot/'

  const proxiedPaths = [
    '/chat', '/guided', '/reports', '/compare-execute', '/speech-to-text',
    '/health', '/download-file', '/explain-category', '/status-errors',
  ]

  return {
    plugins: [react(), versionBuildPlugin(profile)],
    base: basePath,

    server: {
      port: 3000,
      proxy: Object.fromEntries(proxiedPaths.map((path) => [path, target])),
    },
  }
})
