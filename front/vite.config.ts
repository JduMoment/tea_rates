import { defineConfig } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  server: {
    // Запросы /api/* уходят на FastAPI (локально или в docker-compose)
    proxy: {
      '/api': process.env.API_URL ?? 'http://localhost:8000',
    },
  },
})
