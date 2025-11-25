import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 禁用 Service Worker
    headers: {
      'Service-Worker-Allowed': '/'
    }
  },
  // 开发模式下禁用 PWA
  build: {
    rollupOptions: {
      output: {
        manualChunks: undefined
      }
    }
  }
})
