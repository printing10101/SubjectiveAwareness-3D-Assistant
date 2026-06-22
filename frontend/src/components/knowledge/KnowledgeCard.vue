<script setup>
import { getCategoryLabel, getConfidenceStars, formatTime } from './constants.js'

defineProps({
  entry: Object,
})

const emit = defineEmits(['click'])
</script>

<template>
  <div
    class="knowledge-card card"
    @click="emit('click', entry)"
  >
    <div class="card-header">
      <span class="card-category">{{ getCategoryLabel(entry.category) }}</span>
      <span
        v-if="entry.status"
        class="card-status"
        :class="'status-' + entry.status"
      >
        {{ entry.status === 'published' ? '已审核' : entry.status === 'draft' ? '草稿' : entry.status }}
      </span>
    </div>
    <h3 class="card-title">{{ entry.title }}</h3>
    <p
      v-if="entry.summary"
      class="card-summary"
    >
      {{ entry.summary }}
    </p>
    <div class="card-meta">
      <span
        v-if="entry.confidence_score !== undefined"
        class="card-confidence"
        :title="'信心评分：' + (entry.confidence_score * 100).toFixed(0) + '%'"
      >
        {{ getConfidenceStars(entry.confidence_score) }}
      </span>
      <span class="card-time">{{ formatTime(entry.updated_at || entry.created_at) }}</span>
    </div>
    <div
      v-if="entry.tags && entry.tags.length > 0"
      class="card-tags"
    >
      <span
        v-for="tag in entry.tags.slice(0, 3)"
        :key="tag"
        class="card-tag"
      >
        {{ tag }}
      </span>
      <span
        v-if="entry.tags.length > 3"
        class="card-tag card-tag--more"
      >
        +{{ entry.tags.length - 3 }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.knowledge-card {
  padding: 1.25rem;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.knowledge-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.card-category {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  padding: 0.25rem 0.625rem;
  border-radius: 100px;
}

.card-status {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
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

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-summary {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.625rem;
}

.card-confidence {
  font-size: 0.8rem;
  color: #eab308;
  letter-spacing: 0.05em;
}

.card-time {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  padding-top: 0.625rem;
  border-top: 1px solid var(--border-color);
}

.card-tag {
  font-size: 0.7rem;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: 0.2rem 0.5rem;
  border-radius: 100px;
}

.card-tag--more {
  background: none;
  color: var(--text-tertiary);
  font-weight: 500;
}
</style>
