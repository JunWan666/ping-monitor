import { defineConfig } from 'vite'
import { readFileSync, createReadStream } from 'node:fs'
import { createRequire } from 'node:module'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// The standalone public screen is not a Vite entry, but uses the locked ECharts dependency.
function bigscreenMapRuntime() {
  const runtime = createRequire(import.meta.url).resolve('echarts/dist/echarts.min.js')
  const asset = 'bigscreen/echarts.min.js'
  return {
    name: 'bigscreen-map-runtime',
    configureServer(server) {
      server.middlewares.use('/' + asset, (_req, res) => {
        res.setHeader('Content-Type', 'text/javascript; charset=utf-8')
        createReadStream(runtime).pipe(res)
      })
    },
    generateBundle() {
      this.emitFile({ type: 'asset', fileName: asset, source: readFileSync(runtime) })
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    bigscreenMapRuntime(),
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      dts: 'src/auto-imports.d.ts'
    }),
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
    allowedHosts: true,
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
