<script setup>
// 接收 props
const props = defineProps({
  chapters: {
    type: Array,
    required: true,
  },
  reviewItems: {
    type: Object,
    required: true,
  },
  isAllSelected: {
    type: Boolean,
    required: true,
  },
  progressPercent: {
    type: Number,
    required: true,
  },
})

// 发射事件
const emit = defineEmits(['toggle-all', 'toggle-review', 'save-review'])

function handleToggleAll() {
  emit('toggle-all')
}

function handleToggleReview(chapterId) {
  emit('toggle-review', chapterId)
}

function handleSaveReview() {
  emit('save-review')
}
</script>

<template>
  <div class="review-section">
    <div class="review-header">
      <h3 class="review-title">人工审查清单</h3>
      <button
        class="btn-toggle-all"
        @click="handleToggleAll"
      >
        {{ isAllSelected ? '取消全选' : '全选' }}
      </button>
    </div>
    <div class="review-progress">
      <div
        class="progress-bar"
        :style="{ width: `${progressPercent}%` }"
      ></div>
    </div>
    <span class="progress-text">{{ progressPercent }}% 完成</span>
    <ul class="review-list">
      <li
        v-for="chapter in chapters"
        :key="chapter.id"
        class="review-item"
      >
        <label class="review-label">
          <input
            v-model="reviewItems[chapter.id]"
            type="checkbox"
            class="review-checkbox"
            @change="handleToggleReview(chapter.id)"
          >
          <span class="review-text">{{ chapter.title }}</span>
        </label>
      </li>
    </ul>
    <button
      class="btn btn-save"
      @click="handleSaveReview"
    >
      保存审查结果
    </button>
  </div>
</template>

<style scoped>
.review-section {
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-color);
}

.review-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.review-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.btn-toggle-all {
  padding: 0.25rem 0.5rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 0.75rem;
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-toggle-all:hover {
  background: var(--border-color);
}

.review-progress {
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), #22c55e);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  display: block;
  margin-bottom: 1rem;
}

.review-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
}

.review-item {
  margin-bottom: 0.5rem;
}

.review-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.8rem;
}

.review-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.review-text {
  color: var(--text-primary);
}

.btn-save {
  width: 100%;
  padding: 0.625rem;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--border-radius);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-save:hover {
  background: #4338ca;
}
</style>
