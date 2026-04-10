import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    Components({
      dts: 'src/components.d.ts',
      resolvers: [
        ElementPlusResolver({
          importStyle: 'css'
        })
      ]
    })
  ],
  server: {
    host: '0.0.0.0', // 允许局域网访问
    // 禁用 Service Worker
    headers: {
      'Service-Worker-Allowed': '/'
    },
    // 开发环境代理配置
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  // 开发模式下禁用 PWA
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return undefined
          }

          if (id.includes('echarts')) {
            return 'vendor-echarts'
          }

          if (id.includes('element-plus') || id.includes('@element-plus')) {
            return 'vendor-element-plus'
          }

          if (id.includes('xlsx')) {
            return 'vendor-xlsx'
          }

          if (id.includes('vue')) {
            return 'vendor-vue'
          }

          return 'vendor'
        }
      }
    }
  }
})
