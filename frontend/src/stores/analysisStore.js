import { ref, computed } from 'vue'

import { defineStore } from 'pinia'

const MAX_CACHE_SIZE = 50

function hash(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) {
    const code = str.charCodeAt(i)
    h = ((h << 5) - h) + code
    h |= 0
  }
  return `h${  Math.abs(h).toString(36)}`
}

function loadState() {
  try {
    const saved = localStorage.getItem('analysisStore')
    if (saved) {
      const parsed = JSON.parse(saved)
      return {
        currentCaseText: parsed.currentCaseText || '',
        analysisResult: parsed.analysisResult || null,
        currentView: parsed.currentView || 'welcome',
      }
    }
  } catch (e) {
    console.warn('Failed to load state from localStorage:', e)
  }
  return {
    currentCaseText: '',
    analysisResult: null,
    currentView: 'welcome',
  }
}

export const useAnalysisStore = defineStore('analysis', () => {
  const currentCaseText = ref(loadState().currentCaseText)
  const analysisResult = ref(loadState().analysisResult)
  const isLoading = ref(false)
  const currentView = ref(loadState().currentView)
  const error = ref(null)

  const cacheHit = ref(null)
  const responseTime = ref(null)
  const tokensEstimate = ref(null)

  const cache = new Map()

  const cacheKeys = []

  const hasCaseText = computed(() => currentCaseText.value.trim().length > 0)

  const cacheSize = computed(() => cache.size)

  function generateCacheKey(text) {
    return hash(text)
  }

  function evictIfNeeded() {
    while (cache.size >= MAX_CACHE_SIZE && cacheKeys.length > 0) {
      const oldestKey = cacheKeys.shift()
      cache.delete(oldestKey)
    }
  }

  function getCachedResult(cacheKey) {
    if (!cacheKey || !cache.has(cacheKey)) return null
    const idx = cacheKeys.indexOf(cacheKey)
    if (idx > -1) {
      cacheKeys.splice(idx, 1)
      cacheKeys.push(cacheKey)
    }
    return cache.get(cacheKey)
  }

  function setCachedResult(cacheKey, result) {
    if (!cacheKey) return
    if (cache.has(cacheKey)) {
      const idx = cacheKeys.indexOf(cacheKey)
      if (idx > -1) cacheKeys.splice(idx, 1)
      cache.delete(cacheKey)
    }
    evictIfNeeded()
    cache.set(cacheKey, result)
    cacheKeys.push(cacheKey)
  }

  function clearCache() {
    cache.clear()
    cacheKeys.length = 0
  }

  function setCaseText(text) {
    currentCaseText.value = text
    persistState()
  }

  function setAnalysisResult(result) {
    analysisResult.value = result
    persistState()
  }

  function setView(view) {
    currentView.value = view
    persistState()
  }

  function setLoading(loading) {
    isLoading.value = loading
  }

  function setError(err) {
    error.value = err
  }

  function clearError() {
    error.value = null
  }

  function setCacheHit(hit) {
    cacheHit.value = hit
  }

  function setResponseTime(ms) {
    responseTime.value = ms
  }

  function setTokensEstimate(estimate) {
    tokensEstimate.value = estimate
  }

  function navigateToReport() {
    setView('report')
  }

  function navigateToMain() {
    setView('main')
    clearError()
  }

  function clearAnalysis() {
    analysisResult.value = null
    error.value = null
  }

  function persistState() {
    try {
      localStorage.setItem(
        'analysisStore',
        JSON.stringify({
          currentCaseText: currentCaseText.value,
          analysisResult: analysisResult.value,
          currentView: currentView.value,
        })
      )
    } catch (e) {
      console.warn('Failed to persist state:', e)
    }
  }

  function reset() {
    currentCaseText.value = ''
    analysisResult.value = null
    isLoading.value = false
    currentView.value = 'welcome'
    error.value = null
    cacheHit.value = null
    responseTime.value = null
    tokensEstimate.value = null
    clearCache()
    localStorage.removeItem('analysisStore')
  }

  return {
    currentCaseText,
    analysisResult,
    isLoading,
    currentView,
    error,
    cacheHit,
    responseTime,
    tokensEstimate,
    cacheSize,
    hasCaseText,
    generateCacheKey,
    getCachedResult,
    setCachedResult,
    clearCache,
    setCaseText,
    setAnalysisResult,
    setView,
    setLoading,
    setError,
    clearError,
    setCacheHit,
    setResponseTime,
    setTokensEstimate,
    navigateToReport,
    navigateToMain,
    clearAnalysis,
    reset,
  }
})
