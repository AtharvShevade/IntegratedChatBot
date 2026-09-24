import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-proxy target: derived from VITE_API_BASE_URL (frontend/.env.development)
// instead of a port hardcoded here -- one value to change per deployment,
// matching the backend's own single-source-of-truth BACKEND_PORT in .env.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

  const proxiedPaths = [
    '/chat', '/guided', '/reports', '/compare-execute', '/speech-to-text',
    '/health', '/download-file', '/explain-category', '/status-errors',
  ]

  return {
    plugins: [react()],
    base: '/AiChatbot/',
    // base: '/AiChatBot6.0/',

    server: {
      port: 3000,
      proxy: Object.fromEntries(proxiedPaths.map((path) => [path, target])),
    },
  }
})