<script setup>
import { pageSizeOptions } from './constants.js'

const props = defineProps({
  currentPage: Number,
  totalPages: Number,
  pageSize: Number,
  total: Number,
})

const emit = defineEmits(['update:currentPage', 'update:pageSize'])

function goToPage(page) {
  if (page < 1 || page > totalPages || page === currentPage) return
  emit('update:currentPage', page)
}

function getPaginationPages() {
  const pages = []
  const tp = totalPages
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (currentPage > 3) pages.push('...')
    const start = Math.max(2, currentPage - 1)
    const end = Math.min(tp - 1, currentPage + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (currentPage < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
}

function onPageSizeChange(e) {
  emit('update:pageSize', Number(e.target.value))
}
</script>

<template>
  <div
    v-if="totalPages > 1"
    class="pagination"
  >
    <div class="pagination-left">
      <span class="page-info">共 {{ total }} 条</span>
      <select
        :value="pageSize"
        class="page-size-select"
        @change="onPageSizeChange"
      >
        <option
          v-for="size in pageSizeOptions"
          :key="size"
          :value="size"
        >
          每页 {{ size }} 条
        </option>
      </select>
    </div>
    <div class="pagination-pages">
      <button
        class="page-btn"
        :disabled="currentPage <= 1"
        @click="goToPage(currentPage - 1)"
      >
        ‹
      </button>
      <template
        v-for="p in getPaginationPages()"
        :key="p"
      >
        <span
          v-if="p === '...'"
          class="page-ellipsis"
        >…</span>
        <button
          v-else
          class="page-btn"
          :class="{ active: p === currentPage }"
          @click="goToPage(p)"
        >
          {{ p }}
        </button>
      </template>
      <button
        class="page-btn"
        :disabled="currentPage >= totalPages"
        @click="goToPage(currentPage + 1)"
      >
        ›
      </button>
    </div>
  </div>
</template>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 0;
  flex-wrap: wrap;
}

.pagination-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.page-info {
  font-size: 0.825rem;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.page-size-select {
  padding: 0.375rem 2rem 0.375rem 0.625rem;
  font-size: 0.8rem;
  font-family: inherit;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-secondary);
  cursor: pointer;
  outline: none;
  appearance: auto;
}

.pagination-pages {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.page-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
  padding: 0 0.625rem;
  font-size: 0.875rem;
  font-weight: 500;
  font-family: inherit;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.page-btn:hover:not(:disabled):not(.active) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.page-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-ellipsis {
  padding: 0 0.25rem;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

@media (max-width: 767px) {
  .pagination {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>
