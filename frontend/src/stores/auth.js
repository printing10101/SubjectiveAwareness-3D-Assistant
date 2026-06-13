import { ref, computed } from 'vue'

import { defineStore } from 'pinia'

import {
  isAuthenticated as checkAuth,
  getUserRole,
  isAdmin as checkAdmin,
  setToken,
  setTokens as saveTokens,
  clearAuth as removeAuth,
} from '../utils/auth.js'
import { removeItem, getItem } from '../utils/storage.js'

const USER_INFO_KEY = 'user_info'

function loadUserInfo() {
  try {
    const saved = getItem(USER_INFO_KEY)
    return saved ? JSON.parse(saved) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const userInfo = ref(loadUserInfo())
  const isAuthLoading = ref(false)
  const authError = ref(null)

  const isLoggedIn = computed(() => checkAuth())

  const userRole = computed(() => getUserRole())

  const isAdminUser = computed(() => checkAdmin())

  const displayName = computed(() => {
    if (userInfo.value?.display_name) {
      return userInfo.value.display_name
    }
    if (userInfo.value?.username) {
      return userInfo.value.username
    }
    return '用户'
  })

  function setUserInfo(info) {
    userInfo.value = info
    try {
      localStorage.setItem(USER_INFO_KEY, JSON.stringify(info))
    } catch {
      // 静默失败
    }
  }

  function handleLoginSuccess(accessToken, refreshToken, info = null) {
    if (refreshToken) {
      saveTokens(accessToken, refreshToken)
    } else {
      setToken(accessToken)
    }
    if (info) {
      setUserInfo(info)
    }
    authError.value = null
  }

  function handleLogout(router = null) {
    removeAuth()
    userInfo.value = null
    removeItem(USER_INFO_KEY)
    authError.value = null
    if (router) {
      router.push({ name: 'login' })
    }
  }

  function setAuthError(error) {
    authError.value = error
  }

  function clearAuthError() {
    authError.value = null
  }

  function setAuthLoading(loading) {
    isAuthLoading.value = loading
  }

  function reset() {
    handleLogout()
  }

  return {
    userInfo,
    isAuthLoading,
    authError,
    isLoggedIn,
    userRole,
    isAdminUser,
    displayName,
    setUserInfo,
    handleLoginSuccess,
    handleLogout,
    setAuthError,
    clearAuthError,
    setAuthLoading,
    reset,
  }
})