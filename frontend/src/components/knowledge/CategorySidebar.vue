<script setup>
import { categoryTree } from './constants.js'

const props = defineProps({
  selectedCategory: String,
  availableTags: Array,
  selectedTags: Array,
  total: Number,
  isMobile: Boolean,
})

const emit = defineEmits(['selectCategory', 'toggleTag', 'closeDrawer'])

function toggleCategoryExpand(cat) {
  cat.expanded = !cat.expanded
}

function selectCategory(key) {
  emit('selectCategory', key)
}

function toggleTag(tag) {
  emit('toggleTag', tag)
}
</script>

<template>
  <aside class="category-sidebar card">
    <div class="sidebar-header">
      <h3 class="sidebar-title">分类导航</h3>
      <button
        v-if="isMobile"
        class="sidebar-close"
        @click="emit('closeDrawer')"
      >
        ×
      </button>
    </div>

    <div class="category-list">
      <button
        class="category-item category-item--all"
        :class="{ active: !selectedCategory }"
        @click="selectCategory('')"
      >
        <span class="category-icon">📚</span>
        <span class="category-label">全部条目</span>
        <span class="category-count">{{ total }}</span>
      </button>

      <div
        v-for="cat in categoryTree"
        :key="cat.key"
        class="category-group"
      >
        <button
          class="category-item category-item--parent"
          @click="toggleCategoryExpand(cat)"
        >
          <span class="category-expand">{{ cat.expanded ? '▼' : '▶' }}</span>
          <span class="category-label">{{ cat.label }}</span>
        </button>

        <div
          v-show="cat.expanded"
          class="category-children"
        >
          <button
            v-for="child in cat.children"
            :key="child.key"
            class="category-item category-item--child"
            :class="{ active: selectedCategory === child.key }"
            @click="selectCategory(child.key)"
          >
            <span class="category-bullet">•</span>
            <span class="category-label">{{ child.label }}</span>
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="availableTags.length > 0"
      class="tag-filter-section"
    >
      <h4 class="filter-title">标签筛选</h4>
      <div class="tag-filter-list">
        <button
          v-for="tag in availableTags"
          :key="tag"
          class="tag-filter-item"
          :class="{ active: selectedTags.includes(tag) }"
          @click="toggleTag(tag)"
        >
          {{ tag }}
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.category-sidebar {
  width: 260px;
  flex-shrink: 0;
  padding: 1.25rem;
  position: sticky;
  top: 72px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.sidebar-close {
  display: none;
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.625rem;
  font-size: 0.875rem;
  font-family: inherit;
  font-weight: 500;
  color: var(--text-secondary);
  background: none;
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
}

.category-item:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.category-item.active {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
}

.category-item--all {
  font-weight: 600;
  margin-bottom: 0.5rem;
  padding: 0.625rem;
}

.category-item--all .category-icon {
  font-size: 1rem;
}

.category-item--all .category-count {
  margin-left: auto;
  font-size: 0.75rem;
  background: var(--bg-tertiary);
  padding: 0.125rem 0.5rem;
  border-radius: 100px;
  color: var(--text-tertiary);
}

.category-item--parent {
  font-weight: 600;
  color: var(--text-primary);
}

.category-expand {
  font-size: 0.625rem;
  width: 12px;
  text-align: center;
  color: var(--text-tertiary);
  transition: transform var(--transition-fast);
}

.category-item--child {
  padding-left: 2.25rem;
  font-weight: 400;
}

.category-bullet {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.category-children {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.tag-filter-section {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.filter-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.tag-filter-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.tag-filter-item {
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  font-family: inherit;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: 100px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tag-filter-item:hover {
  border-color: var(--border-color);
  color: var(--text-primary);
}

.tag-filter-item.active {
  background: rgba(79, 70, 229, 0.1);
  color: var(--color-primary);
  border-color: var(--color-primary);
}

@media (max-width: 767px) {
  .sidebar-close {
    display: block;
  }
}
</style>
