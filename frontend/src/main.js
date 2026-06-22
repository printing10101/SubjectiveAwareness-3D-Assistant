import * as Sentry from '@sentry/vue'
import { createApp } from 'vue'

import axios from 'axios'
import { createPinia } from 'pinia'

import './assets/styles/tokens.css'
import './assets/styles/base.css'

import App from './App.vue'
import router from './router/index.js'
import { refreshAccessToken, clearAuth } from './utils/auth.js'
import {
  formatUserMessage,
  logError,
  LogLevel,
  collectContext,
  isRetryable,
} from './utils/errorHandler.js'
import errorPlugin from './utils/errorPlugin.js'

// =====================================================================
// Sentry 错误追踪与性能监控 - 配置读取
// =====================================================================
// 仅当 VITE_SENTRY_DSN 存在且非空时才启用 Sentry。
// 未配置时应用完全正常运行，不产生任何 Sentry 副作用或网络请求。
//
// 集成模块：
//   - browserTracingIntegration: 捕获前端性能、路由变化、资源加载
//   - replayIntegration: 用户会话重放，便于复现错误
// =====================================================================
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN
const SENTRY_ENVIRONMENT =
  import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE
const SENTRY_TRACES_SAMPLE_RATE = Number(
  import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? 0.1,
)
const SENTRY_REPLAYS_SESSION_SAMPLE_RATE = Number(
  import.meta.env.VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE ?? 0.0,
)
const SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE = Number(
  import.meta.env.VITE_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE ?? 1.0,
)
export const SENTRY_ENABLED = Boolean(SENTRY_DSN && SENTRY_DSN.trim())

// =====================================================================
// Axios 默认配置与拦截器
// =====================================================================
const pinia = createPinia()
const app = createApp(App)

// 必须在 createApp 之后初始化 Sentry（需要传入 app 引用以注入错误处理）
if (SENTRY_ENABLED) {
  Sentry.init({
    app,
    dsn: SENTRY_DSN,
    environment: SENTRY_ENVIRONMENT,
    integrations: [
      Sentry.browserTracingIntegration({ router }),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate: Math.max(0, Math.min(1, SENTRY_TRACES_SAMPLE_RATE)),
    replaysSessionSampleRate: Math.max(
      0,
      Math.min(1, SENTRY_REPLAYS_SESSION_SAMPLE_RATE),
    ),
    replaysOnErrorSampleRate: Math.max(
      0,
      Math.min(1, SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE),
    ),
    attachStacktrace: true,
    sendDefaultPii: false,
    tracePropagationTargets: [/^\/api\//, 'localhost', '127.0.0.1'],
  })

  Sentry.setTag('app_name', 'Legal Analysis Frontend')
  Sentry.setTag('app_env', SENTRY_ENVIRONMENT)

  // eslint-disable-next-line no-console
  console.info(
    `[Sentry] 已启用: environment=${SENTRY_ENVIRONMENT}, tracesSampleRate=${SENTRY_TRACES_SAMPLE_RATE}`,
  )
}

axios.defaults.baseURL = ''
axios.defaults.timeout = 30000
axios.defaults.headers.common['Content-Type'] = 'application/json'

const MAX_RETRIES = 2

axios.interceptors.request.use(
  (config) => {
    config.metadata = { startTime: new Date() }
    config._retryCount = config._retryCount || 0
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (SENTRY_ENABLED) {
      Sentry.addBreadcrumb({
        category: 'http',
        type: 'http',
        level: 'info',
        data: {
          method: config.method?.toUpperCase(),
          url: config.url,
        },
      })
    }
    return config
  },
  (error) => {
    logError(LogLevel.ERROR, '请求发送失败', collectContext(error))
    if (SENTRY_ENABLED) {
      Sentry.addBreadcrumb({
        category: 'http',
        level: 'error',
        data: { message: String(error?.message || error) },
      })
    }
    return Promise.reject(error)
  }
)

axios.interceptors.response.use(
  (response) => {
    const duration = new Date() - response.config.metadata.startTime
    logError(LogLevel.INFO, `请求成功`, {
      url: response.config.url,
      status: response.status,
      duration: `${duration}ms`,
    })
    if (SENTRY_ENABLED) {
      Sentry.addBreadcrumb({
        category: 'http',
        level: 'info',
        data: {
          url: response.config.url,
          status: response.status,
          duration: `${duration}ms`,
        },
      })
    }
    return response
  },
  async (error) => {
    if (!error.config) {
      return Promise.reject(error)
    }

    const config = error.config
    const status = error.response?.status
    const context = collectContext(error)
    logError(LogLevel.WARN, `API 响应错误: ${status || '网络错误'}`, context)

    if (SENTRY_ENABLED) {
      Sentry.addBreadcrumb({
        category: 'http',
        level: status >= 500 ? 'error' : 'warning',
        data: {
          url: config.url,
          method: config.method?.toUpperCase(),
          status,
        },
      })
      // 5xx 服务端错误上报 Sentry（4xx 通常是客户端问题，无需上报）
      if (status && status >= 500) {
        Sentry.captureException(error, {
          tags: { feature: 'api_response' },
          extra: { url: config.url, method: config.method },
        })
      }
    }

    // 401 错误处理：尝试刷新 token，失败则跳转登录页
    if (status === 401 && !config._retryAuth) {
      config._retryAuth = true
      try {
        const newToken = await refreshAccessToken()
        config.headers.Authorization = `Bearer ${newToken}`
        return axios(config)  // 成功刷新后重试原请求
      } catch (refreshError) {
        // Token 刷新失败，清除认证状态并跳转登录页
        clearAuth()
        router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
        // 返回拒绝的 Promise，通知调用方认证失败
        return Promise.reject({
          message: '认证已过期，请重新登录',
          status: 401,
          requiresLogin: true,
        })
      }
    }

    if (status === 403) {
      router.push({ name: 'forbidden' })
      return Promise.reject(formatRejection(error, 403))
    }

    if (status === 404) {
      return Promise.reject(formatRejection(error, 404))
    }

    if (status === 413) {
      return Promise.reject(formatRejection(error, 413))
    }

    if (status === 429) {
      const retryAfter = error.response.headers['retry-after']
      const delay = retryAfter ? parseInt(retryAfter) * 1000 : 3000
      if (config._retryCount < MAX_RETRIES) {
        config._retryCount++
        logError(LogLevel.WARN, `请求限流，${delay / 1000}s 后重试 (${config._retryCount}/${MAX_RETRIES})`, { url: config.url })
        await new Promise((resolve) => setTimeout(resolve, delay))
        return axios(config)
      }
      return Promise.reject(formatRejection(error, 429))
    }

    if (isRetryable(error) && config._retryCount < MAX_RETRIES) {
      config._retryCount++
      const delay = Math.min(1000 * Math.pow(2, config._retryCount), 4000)
      logError(LogLevel.WARN, `服务器错误，${delay}ms 后重试 (${config._retryCount}/${MAX_RETRIES})`, { url: config.url })
      await new Promise((resolve) => setTimeout(resolve, delay))
      return axios(config)
    }

    if (!error.response) {
      return Promise.reject({
        message: '网络连接失败，请检查网络或服务器是否正常运行',
        status: 0,
      })
    }

    return Promise.reject(formatRejection(error, status))
  }
)

function formatRejection(error, status) {
  return {
    message: formatUserMessage(error),
    status,
    data: error.response?.data || null,
    originalError: error,
  }
}

app.config.globalProperties.$axios = axios
app.use(errorPlugin)
app.use(pinia)
app.use(router)
app.mount('#app')
