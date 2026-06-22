<script setup>
// 接收 props
const props = defineProps({
  chapters: {
    type: Array,
    required: true,
  },
  activeChapter: {
    type: String,
    required: true,
  },
  markedSections: {
    type: Object,
    required: true,
  },
})

// 发射事件
const emit = defineEmits(['chapter-click'])

function handleChapterClick(chapterId) {
  emit('chapter-click', chapterId)
}

function isMarked(chapterId) {
  return props.markedSections.has(chapterId)
}
</script>

<template>
  <nav class="chapter-nav">
    <h3 class="nav-title">报告目录</h3>
    <ul class="chapter-list">
      <li
        v-for="chapter in chapters"
        :key="chapter.id"
        class="chapter-item"
        :class="{ active: activeChapter === chapter.id }"
        @click="handleChapterClick(chapter.id)"
      >
        <span class="chapter-icon">{{ chapter.icon }}</span>
        <span class="chapter-name">{{ chapter.title }}</span>
        <span
          v-if="isMarked(chapter.id)"
          class="mark-badge"
        >✓</span>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.nav-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.chapter-list {
  list-style: none;
  padding: 0;
  margin: 0 0 2rem;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: 0.875rem;
  color: var(--text-primary);
}

.chapter-item:hover {
  background: var(--bg-tertiary);
}

.chapter-item.active {
  background: rgba(79, 70, 229, 0.1);
  color: var(--color-primary);
  font-weight: 500;
}

.chapter-icon {
  font-size: 1rem;
}

.chapter-name {
  flex: 1;
}

.mark-badge {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: white;
  border-radius: 50%;
  font-size: 0.625rem;
}
</style>
