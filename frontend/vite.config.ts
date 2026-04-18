import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/review': { target: 'http://localhost:8000', changeOrigin: true },
      '/inject-memory': { target: 'http://localhost:8000', changeOrigin: true },
      '/projects': { target: 'http://localhost:8000', changeOrigin: true },
      '/memory': { target: 'http://localhost:8000', changeOrigin: true },
      '/reviews': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    }
  }
})

