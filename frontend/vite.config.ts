import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/review': 'http://localhost:8000',
      '/inject-memory': 'http://localhost:8000',
    }
  }
})

