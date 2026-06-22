<script setup>
import { ref, computed, watch } from 'vue'

import axios from 'axios'

const props = defineProps({
  errorMsg: {
    type: Object,
    default: () => ({ value: null }),
  },
})

const logs = ref([])
const logsTotal = ref(0)
const logsPage = ref(1)
const logsPageSize = ref(20)
const logLevelFilter = ref('')
const logSearch = ref('')
const isLogsLoading = ref(false)

const logsTotalPages = computed(() => Math.max(1, Math.ceil(logsTotal.value / logsPageSize.value)))

const logLevels = [
  { value: '', label: '全部级别' },
  { value: 'INFO', label: 'INFO' },
  { value: 'WARNING', label: 'WARNING' },
  { value: 'ERROR', label: 'ERROR' },
  { value: 'DEBUG', label: 'DEBUG' },
]

watch([logLevelFilter, logSearch], () => {
  logsPage.value = 1
  fetchLogs()
})

async function fetchLogs() {
  isLogsLoading.value = true
  try {
    const params = { page: logsPage.value, page_size: logsPageSize.value }
    if (logLevelFilter.value) params.log_level = logLevelFilter.value
    if (logSearch.value.trim()) params.search = logSearch.value.trim()
    const res = await axios.get('/api/logs', { params })
    logs.value = res.data.items || []
    logsTotal.value = res.data.total || 0
  } catch {
    logs.value = []
    logsTotal.value = 0
  } finally {
    isLogsLoading.value = false
  }
}

function handleGoToLogsPage(page) {
  if (page < 1 || page > logsTotalPages.value || page === logsPage.value) return
  logsPage.value = page
  fetchLogs()
}

function getLogsPaginationPages() {
  const pages = []
  const tp = logsTotalPages.value
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (logsPage.value > 3) pages.push('...')
    const start = Math.max(2, logsPage.value - 1)
    const end = Math.min(tp - 1, logsPage.value + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (logsPage.value < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
}

function getLogLevelClass(level) {
  const map = {
    ERROR: 'log-error',
    WARNING: 'log-warning',
    INFO: 'log-info',
    DEBUG: 'log-debug',
  }
  return map[level] || 'log-info'
}

function formatTime(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return dateStr
  }
}

defineExpose({
  fetchLogs,
  logs,
  logsTotal,
  logsPage,
  logsPageSize,
  logLevelFilter,
  logSearch,
  isLogsLoading,
  logsTotalPages,
  handleGoToLogsPage,
  getLogsPaginationPages,
  getLogLevelClass,
  formatTime,
  logLevels,
})
</script>

<template>
  <div class="logs-panel">
    <div class="panel-header">
      <h3 class="panel-title">系统日志</h3>
      <button class="btn btn-ghost btn-sm" @click="fetchLogs" :disabled="isLogsLoading">
        <span class="btn-icon">🔄</span>
        刷新
      </button>
    </div>

    <div class="filter-bar">
      <select v-model="logLevelFilter" class="filter-select">
        <option v-for="level in logLevels" :key="level.value" :value="level.value">
          {{ level.label }}
        </option>
      </select>
      <input
        v-model="logSearch"
        type="text"
        class="search-input"
        placeholder="搜索日志内容..."
      />
    </div>

    <div v-if="isLogsLoading" class="loading-state">加载中...</div>

    <div v-else class="logs-list">
      <div v-for="(log, index) in logs" :key="index" class="log-entry">
        <div class="log-header">
          <span class="log-level" :class="getLogLevelClass(log.level)">{{ log.level }}</span>
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
        </div>
        <div class="log-message">{{ log.message }}</div>
        <div v-if="log.source" class="log-source">{{ log.source }}</div>
      </div>

      <div v-if="logs.length === 0" class="empty-state">
        <p>暂无日志</p>
      </div>
    </div>

    <div v-if="logsTotalPages > 1" class="pagination">
      <button
        class="pagination-btn"
        :disabled="logsPage === 1"
        @click="handleGoToLogsPage(logsPage - 1)"
      >
        ‹
      </button>
      <button
        v-for="page in getLogsPaginationPages()"
        :key="page"
        class="pagination-btn"
        :class="{ active: page === logsPage, disabled: page === '...' }"
        :disabled="page === '...'"
        @click="handleGoToLogsPage(page)"
      >
        {{ page }}
      </button>
      <button
        class="pagination-btn"
        :disabled="logsPage === logsTotalPages"
        @click="handleGoToLogsPage(logsPage + 1)"
      >
        ›
      </button>
    </div>
  </div>
</template>

<style scoped>
.logs-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: var(--text-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.filter-bar {
  display: flex;
  gap: var(--space-2);
}

.filter-select {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--bg-primary);
}

.search-input {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.loading-state,
.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-tertiary);
}

.logs-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.log-entry {
  padding: var(--space-3);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.log-level {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-weight-medium);
}

.log-level.log-error {
  background: var(--color-danger-light);
  color: var(--color-danger);
}

.log-level.log-warning {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.log-level.log-info {
  background: var(--color-info-light);
  color: var(--color-info);
}

.log-level.log-debug {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.log-time {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.log-message {
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: var(--leading-relaxed);
  word-break: break-word;
}

.log-source {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.pagination {
  display: flex;
  justify-content: center;
  gap: var(--space-1);
  margin-top: var(--space-4);
}

.pagination-btn {
  padding: var(--space-1) var(--space-2);
  min-width: 32px;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.pagination-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: var(--border-secondary);
}

.pagination-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
