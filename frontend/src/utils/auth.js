import * as Sentry from '@sentry/vue'
import axios from 'axios'

const TOKEN_KEY = 'auth_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

let refreshPromise = null

export function isAuthenticated() {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) return false
  try {
    if (token.startsWith('eyJ')) {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const now = Math.floor(Date.now() / 1000)
      return payload.exp > now
    }
    return true
  } catch {
    return true
  }
}

export function getUserRole() {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) return null
  try {
    if (token.startsWith('eyJ')) {
      const payload = JSON.parse(atob(token.split('.')[1]))
      return payload.role || payload.user_role || null
    }
    return null
  } catch {
    return null
  }
}

export function isAdmin() {
  const role = getUserRole()
  return role === 'admin' || role === 'administrator'
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
  syncSentryUserContext()
}

export function setTokens(accessToken, refreshToken) {
  localStorage.setItem(TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  syncSentryUserContext()
  Sentry.addBreadcrumb({
    category: 'auth',
    level: 'info',
    message: 'tokens_updated',
  })
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  // 退出登录时清除 Sentry 用户上下文
  Sentry.setUser(null)
  Sentry.addBreadcrumb({
    category: 'auth',
    level: 'info',
    message: 'auth_cleared',
  })
}

export function clearAuthAndRedirect(router) {
  clearAuth()
  if (router) {
    router.push({ name: 'login', query: { redirect: window.location.pathname } })
  }
}

function syncSentryUserContext() {
  // 同步用户信息到 Sentry，便于错误定位
  // 仅设置非敏感的标识字段，邮箱/电话等敏感信息由 Sentry 自动过滤
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) {
    Sentry.setUser(null)
    return
  }
  try {
    if (token.startsWith('eyJ')) {
      const payload = JSON.parse(atob(token.split('.')[1]))
      Sentry.setUser({
        id: String(payload.sub || payload.user_id || 'unknown'),
        username: payload.username || payload.name,
        role: payload.role || payload.user_role,
      })
    }
  } catch {
    Sentry.setUser({ id: 'unknown' })
  }
}

export async function refreshAccessToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    clearAuth()
    throw new Error('No refresh token available')
  }

  if (refreshPromise) {
    return refreshPromise
  }

  Sentry.addBreadcrumb({
    category: 'auth',
    level: 'info',
    message: 'refresh_token_requested',
  })

  refreshPromise = axios
    .post('/api/auth/refresh', { refresh_token: refreshToken })
    .then((res) => {
      const { access_token, refresh_token } = res.data
      setTokens(access_token, refresh_token || refreshToken)
      return access_token
    })
    .catch((err) => {
      clearAuth()
      throw err
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}
