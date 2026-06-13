import { ref, computed } from 'vue'

import { defineStore } from 'pinia'

import apiClient from '../api/client.js'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const entries = ref([])
  const currentEntry = ref(null)
  const tags = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref(null)

  const hasEntries = computed(() => entries.value.length > 0)

  const hasCurrentEntry = computed(() => currentEntry.value !== null)

  function setLoading(value) {
    loading.value = value
  }

  function setError(err) {
    error.value = typeof err === 'string' ? err : (err?.message || '操作失败，请稍后重试')
  }

  function clearError() {
    error.value = null
  }

  async function fetchEntries(params = {}) {
    setLoading(true)
    clearError()

    try {
      const queryParams = {}

      if (params.page) queryParams.page = params.page
      if (params.pageSize) queryParams.page_size = params.pageSize
      if (params.search) queryParams.search = params.search
      if (params.tags && params.tags.length > 0) queryParams.tags = params.tags.join(',')
      if (params.category) queryParams.category = params.category
      if (params.sortBy) queryParams.sort_by = params.sortBy
      if (params.sortOrder) queryParams.sort_order = params.sortOrder

      const response = await apiClient.get('/api/knowledge', { params: queryParams })
      entries.value = response.data.entries || response.data.items || []
      total.value = response.data.total || 0
      return { entries: entries.value, total: total.value }
    } catch (err) {
      setError(err)
      entries.value = []
      total.value = 0
      throw err
    } finally {
      setLoading(false)
    }
  }

  async function fetchEntry(id) {
    setLoading(true)
    clearError()

    try {
      const response = await apiClient.get(`/api/knowledge/${id}`)
      currentEntry.value = response.data
      return response.data
    } catch (err) {
      setError(err)
      currentEntry.value = null
      throw err
    } finally {
      setLoading(false)
    }
  }

  async function createEntry(data) {
    setLoading(true)
    clearError()

    try {
      const response = await apiClient.post('/api/knowledge', data)
      if (response.data) {
        entries.value.unshift(response.data)
      }
      return response.data
    } catch (err) {
      setError(err)
      throw err
    } finally {
      setLoading(false)
    }
  }

  async function updateEntry(id, data) {
    setLoading(true)
    clearError()

    try {
      const response = await apiClient.put(`/api/knowledge/${id}`, data)
      if (response.data) {
        currentEntry.value = response.data
        const index = entries.value.findIndex((e) => e.id === id || e._id === id)
        if (index !== -1) {
          entries.value[index] = response.data
        }
      }
      return response.data
    } catch (err) {
      setError(err)
      throw err
    } finally {
      setLoading(false)
    }
  }

  async function deleteEntry(id) {
    setLoading(true)
    clearError()

    try {
      await apiClient.delete(`/api/knowledge/${id}`)
      entries.value = entries.value.filter((e) => e.id !== id && e._id !== id)
      if (currentEntry.value && (currentEntry.value.id === id || currentEntry.value._id === id)) {
        currentEntry.value = null
      }
      return true
    } catch (err) {
      setError(err)
      throw err
    } finally {
      setLoading(false)
    }
  }

  async function fetchTags() {
    try {
      const response = await apiClient.get('/api/knowledge/tags')
      tags.value = response.data.tags || response.data || []
      return tags.value
    } catch {
      tags.value = []
      return []
    }
  }

  function clearCurrentEntry() {
    currentEntry.value = null
  }

  function reset() {
    entries.value = []
    currentEntry.value = null
    tags.value = []
    total.value = 0
    loading.value = false
    error.value = null
  }

  return {
    entries,
    currentEntry,
    tags,
    total,
    loading,
    error,
    hasEntries,
    hasCurrentEntry,
    fetchEntries,
    fetchEntry,
    createEntry,
    updateEntry,
    deleteEntry,
    fetchTags,
    clearCurrentEntry,
    clearError,
    setLoading,
    setError,
    reset,
  }
})