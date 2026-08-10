import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/algorithm': 'http://localhost:8000',
      '/data': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
