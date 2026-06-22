<script setup>
// 接收 props
const props = defineProps({
  chapter: {
    type: Object,
    required: true,
  },
  chapterData: {
    type: Object,
    default: () => ({}),
  },
  isMarked: {
    type: Boolean,
    default: false,
  },
})

// 发射事件
const emit = defineEmits(['mark-section'])

function handleMarkSection() {
  emit('mark-section', props.chapter.id)
}
</script>

<template>
  <div
    :id="`chapter-${chapter.id}`"
    class="chapter-section"
  >
    <div class="chapter-header">
      <h2 class="chapter-title">
        <span class="title-icon">{{ chapter.icon }}</span>
        {{ chapterData?.title || chapter.title }}
      </h2>
      <button
        class="btn-mark"
        :class="{ marked: isMarked }"
        @click="handleMarkSection"
      >
        {{ isMarked ? '✓ 已标记' : '📌 标记' }}
      </button>
    </div>

    <div class="chapter-body">
      <template v-if="chapterData?.sections">
        <div
          v-for="(section, idx) in chapterData.sections"
          :key="idx"
          class="section-block"
        >
          <h4
            v-if="section.heading"
            class="section-heading"
          >
            {{ section.heading }}
          </h4>
          <p
            v-if="section.content"
            class="section-content"
          >
            {{ section.content }}
          </p>

          <!-- 特殊字段展示 -->
          <div
            v-if="section.tier_label"
            class="tier-badge"
          >
            档级: {{ section.tier_label }}
          </div>

          <div
            v-if="section.sentence_band"
            class="sentence-badge"
          >
            量刑区间: {{ section.sentence_band }}
          </div>

          <div
            v-if="section.conclusion"
            class="conclusion-badge"
          >
            结论: {{ section.conclusion }}
          </div>

          <!-- 标签展示 -->
          <div
            v-if="section.tags"
            class="tags-container"
          >
            <span
              v-for="tag in section.tags"
              :key="tag"
              class="tag-item"
            >{{ tag }}</span>
          </div>

          <!-- 法律依据 -->
          <div
            v-if="section.laws"
            class="laws-container"
          >
            <div
              v-for="law in section.laws"
              :key="law.article"
              class="law-item"
            >
              <strong>{{ law.law }} {{ law.article }}:</strong>
              {{ law.content }}
            </div>
          </div>
        </div>
      </template>

      <div
        v-else
        class="empty-section"
      >
        暂无内容
      </div>
    </div>
  </div>
</template>

<style scoped>
.chapter-section {
  background: white;
  border-radius: var(--border-radius-lg);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--shadow-sm);
}

.chapter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--border-color);
}

.chapter-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.title-icon {
  font-size: 1.25rem;
}

.btn-mark {
  padding: 0.375rem 0.75rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-mark:hover {
  background: var(--border-color);
}

.btn-mark.marked {
  background: rgba(79, 70, 229, 0.1);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.chapter-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-block {
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
}

.section-heading {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.5rem;
}

.section-content {
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--text-primary);
  margin: 0;
  white-space: pre-wrap;
}

.tier-badge,
.sentence-badge,
.conclusion-badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-top: 0.5rem;
  margin-right: 0.5rem;
}

.tier-badge {
  background: #fef3c7;
  color: #92400e;
}

.sentence-badge {
  background: #dcfce7;
  color: #166534;
}

.conclusion-badge {
  background: #f3e8ff;
  color: #6b21a8;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  margin-top: 0.5rem;
}

.tag-item {
  padding: 0.25rem 0.5rem;
  background: var(--bg-tertiary);
  border-radius: 12px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.laws-container {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: #f0f9ff;
  border-radius: var(--border-radius);
  border-left: 3px solid #0ea5e9;
}

.law-item {
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--text-primary);
  margin-bottom: 0.375rem;
}

.law-item:last-child {
  margin-bottom: 0;
}

.empty-section {
  padding: 2rem;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .chapter-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
}
</style>
