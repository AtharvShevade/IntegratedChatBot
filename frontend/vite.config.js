import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Proxy API calls to the FastAPI backend — avoids CORS issues in development
    proxy: {
      // Chatbot backend — run with: uvicorn backend.main:app --port 8001 --reload
      '/chat':           'http://localhost:8001',
      '/guided':         'http://localhost:8001',
      '/reports':        'http://localhost:8001',
      '/compare-execute':'http://localhost:8001',
      '/speech-to-text': 'http://localhost:8001',
      '/health':         'http://localhost:8001',
      '/download-file':  'http://localhost:8001',
      '/variance':       'http://localhost:8001',
    },
  },
})
