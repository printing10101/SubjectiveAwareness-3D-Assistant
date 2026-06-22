<script setup>
import { getCategoryLabel, formatTime } from './constants.js'

defineProps({
  entry: Object,
})

const emit = defineEmits(['click'])
</script>

<template>
  <div
    class="list-row"
    @click="emit('click', entry)"
  >
    <span class="list-col list-col--title">
      <span class="list-title-text">{{ entry.title }}</span>
    </span>
    <span class="list-col list-col--category">{{ getCategoryLabel(entry.category) }}</span>
    <span class="list-col list-col--status">
      <span
        class="status-tag"
        :class="'status-' + (entry.status || 'draft')"
      >
        {{ entry.status === 'published' ? '已审核' : entry.status === 'draft' ? '草稿' : (entry.status || '草稿') }}
      </span>
    </span>
    <span class="list-col list-col--confidence">
      <span class="confidence-text">{{ entry.confidence_score ? (entry.confidence_score * 100).toFixed(0) + '%' : '—' }}</span>
    </span>
    <span class="list-col list-col--time">{{ formatTime(entry.updated_at || entry.created_at) }}</span>
  </div>
</template>

<style scoped>
.list-row {
  display: flex;
  align-items: center;
  padding: 0.875rem 1.25rem;
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.list-row:last-child {
  border-bottom: none;
}

.list-row:hover {
  background: var(--bg-secondary);
}

.list-col {
  flex-shrink: 0;
}

.list-col--title {
  flex: 1;
  min-width: 0;
}

.list-title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  color: var(--text-primary);
}

.list-col--category {
  width: 120px;
  font-size: 0.8rem;
  color: var(--color-primary);
  font-weight: 500;
}

.list-col--status {
  width: 80px;
  text-align: center;
}

.list-col--confidence {
  width: 100px;
  text-align: center;
}

.confidence-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.list-col--time {
  width: 130px;
  text-align: right;
  font-size: 0.8rem;
  color: var(--text-tertiary);
  font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
}

.status-tag {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  font-size: 0.7rem;
  font-weight: 600;
  border-radius: 100px;
}

.status-published {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #86efac;
}

.status-draft {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}

.status-review {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

@media (max-width: 767px) {
  .list-row {
    padding: 0.625rem 0.75rem;
  }

  .list-col--category {
    display: none;
  }

  .list-col--status {
    width: 60px;
  }

  .list-col--confidence {
    width: 60px;
  }

  .list-col--time {
    display: none;
  }
}
</style>
