import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: true, // Necessário para o Docker expor a porta
    port: 5173,
    proxy: {
      // Redireciona chamadas REST (ex: fetch('/api/history'))
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        secure: false,
      },
      // Redireciona chamadas WebSocket (ex: ws://localhost/ws/logs)
      '/ws': {
        target: 'ws://backend:8000',
        ws: true,
        changeOrigin: true
      }
    }
  }
})