// vite.config.js
// Configuración de Vite para desarrollo y producción.
// El proxy redirige /api al backend FastAPI y /ws al endpoint WebSocket
// durante el desarrollo local sin necesidad de Nginx.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      // Proxy HTTP para la API REST
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      // Proxy WebSocket — ws:true es obligatorio para que Vite
      // maneje correctamente el protocolo de actualización WS
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})