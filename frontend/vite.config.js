import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: "/AICHATBOT/",
  plugins: [react()],

  server: {
    port: 3000,
    proxy: {
      '/chat': 'http://localhost:8001',
      '/guided': 'http://localhost:8001',
      '/reports': 'http://localhost:8001',
      '/compare-execute': 'http://localhost:8001',
      '/speech-to-text': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
      '/download-file': 'http://localhost:8001',
      '/explain-category': 'http://localhost:8001',
      '/status-errors': 'http://localhost:8001',
    },
  },
})