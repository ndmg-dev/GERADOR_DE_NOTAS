import react from '@vitejs/plugin-react'
import path from 'node:path'
import { defineConfig } from 'vite'

// Dentro do Docker o backend é alcançado pelo nome do serviço; fora dele, por localhost.
const apiTarget = process.env.VITE_API_PROXY_TARGET
  ?? (process.env.IN_DOCKER === 'true' ? 'http://backend:8000' : 'http://localhost:8000')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Bind mounts do Docker no Windows não propagam eventos de arquivo; sem
    // polling o HMR não enxerga as edições feitas fora do contêiner.
    watch: process.env.IN_DOCKER === 'true' ? { usePolling: true, interval: 300 } : undefined,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
