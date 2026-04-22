import { defineAsyncComponent, h } from 'vue'

const RELOAD_MARK_KEY = 'ping-monitor:asset-reload-at'
const RELOAD_WINDOW_MS = 15000

const RETRYABLE_PATTERNS = [
  'failed to fetch dynamically imported module',
  'fetch dynamically imported module',
  'importing a module script failed',
  'chunkloaderror',
  'loading chunk',
  'unable to preload css'
]

const AsyncLoadError = {
  name: 'AsyncLoadError',
  props: {
    error: {
      type: Object,
      default: null
    }
  },
  setup(props) {
    const refreshPage = () => {
      if (typeof window !== 'undefined') {
        window.location.reload()
      }
    }

    return () =>
      h(
        'div',
        {
          style: {
            minHeight: '240px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '32px'
          }
        },
        [
          h(
            'div',
            {
              style: {
                width: '100%',
                maxWidth: '520px',
                padding: '24px',
                borderRadius: '16px',
                border: '1px solid rgba(64, 158, 255, 0.18)',
                background: '#fff',
                boxShadow: '0 10px 30px rgba(15, 23, 42, 0.08)',
                textAlign: 'center'
              }
            },
            [
              h(
                'div',
                {
                  style: {
                    fontSize: '18px',
                    fontWeight: '600',
                    color: '#303133',
                    marginBottom: '10px'
                  }
                },
                '页面模块加载失败'
              ),
              h(
                'div',
                {
                  style: {
                    fontSize: '14px',
                    lineHeight: '1.7',
                    color: '#606266',
                    marginBottom: '16px'
                  }
                },
                props.error?.message?.includes('import')
                  ? '检测到前端资源可能刚刚更新，刷新页面后通常可以恢复。'
                  : '当前模块暂时不可用，可以刷新页面后重试。'
              ),
              h(
                'button',
                {
                  type: 'button',
                  onClick: refreshPage,
                  style: {
                    border: 'none',
                    borderRadius: '999px',
                    padding: '10px 18px',
                    background: '#409eff',
                    color: '#fff',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }
                },
                '刷新页面'
              )
            ]
          )
        ]
      )
  }
}

const clearReloadMark = () => {
  if (typeof window === 'undefined') {
    return
  }

  sessionStorage.removeItem(RELOAD_MARK_KEY)
}

const shouldReloadOnce = () => {
  if (typeof window === 'undefined') {
    return false
  }

  const now = Date.now()
  const lastReloadAt = Number(sessionStorage.getItem(RELOAD_MARK_KEY) || 0)

  if (now - lastReloadAt < RELOAD_WINDOW_MS) {
    return false
  }

  sessionStorage.setItem(RELOAD_MARK_KEY, String(now))
  return true
}

const isRetryableAsyncError = (error) => {
  const message = String(error?.message || error || '').toLowerCase()
  return RETRYABLE_PATTERNS.some((pattern) => message.includes(pattern))
}

export const defineAsyncPage = (loader, options = {}) =>
  defineAsyncComponent({
    loader: async () => {
      const component = await loader()
      clearReloadMark()
      return component
    },
    delay: options.delay ?? 120,
    timeout: options.timeout ?? 20000,
    suspensible: false,
    errorComponent: options.errorComponent ?? AsyncLoadError,
    onError(error, retry, fail, attempts) {
      if (isRetryableAsyncError(error) && attempts <= 1) {
        retry()
        return
      }

      if (isRetryableAsyncError(error) && shouldReloadOnce()) {
        window.location.reload()
        return
      }

      fail(error)
    }
  })

export const loadRouteWithRetry = (loader) => async () => {
  try {
    const component = await loader()
    clearReloadMark()
    return component
  } catch (error) {
    if (isRetryableAsyncError(error) && shouldReloadOnce()) {
      window.location.reload()
      return new Promise(() => {})
    }

    throw error
  }
}

export const installAssetReloadGuard = () => {
  if (typeof window === 'undefined') {
    return
  }

  window.addEventListener('vite:preloadError', (event) => {
    event.preventDefault()

    if (shouldReloadOnce()) {
      window.location.reload()
    }
  })
}
