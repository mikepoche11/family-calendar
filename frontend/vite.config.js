import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development, API calls go to the backend on :8000
export default defineConfig({
  plugins: [react()],
  server: { host: true, proxy: { '/api': 'http://localhost:8000' } },
})
