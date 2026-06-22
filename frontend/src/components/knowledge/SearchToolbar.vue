<script setup>
import { sortOptions } from './constants.js'

const props = defineProps({
  searchKeyword: String,
  sortBy: String,
  sortOrder: String,
  viewMode: String,
})

const emit = defineEmits(['update:searchKeyword', 'update:sortBy', 'toggleSortOrder', 'setViewMode'])

function onSearchInput(e) {
  emit('update:searchKeyword', e.target.value)
}

function clearSearch() {
  emit('update:searchKeyword', '')
}

function onSortChange(e) {
  emit('update:sortBy', e.target.value)
}

function toggleSortOrder() {
  emit('toggleSortOrder')
}

function setViewMode(mode) {
  emit('setViewMode', mode)
}
</script>

<template>
  <div class="toolbar card">
    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input
        :value="searchKeyword"
        type="text"
        class="search-input"
        placeholder="搜索知识条目..."
        @input="onSearchInput"
      />
      <button
        v-if="searchKeyword"
        class="search-clear"
        @click="clearSearch"
      >
        ×
      </button>
    </div>

    <div class="toolbar-actions">
      <select
        :value="sortBy"
        class="toolbar-select"
        @change="onSortChange"
      >
        <option
          v-for="opt in sortOptions"
          :key="opt.value"
          :value="opt.value"
        >
          {{ opt.label }}
        </option>
      </select>

      <button
        class="sort-order-btn"
        :title="sortOrder === 'desc' ? '降序' : '升序'"
        @click="toggleSortOrder"
      >
        {{ sortOrder === 'desc' ? '↓' : '↑' }}
      </button>

      <div class="view-toggle">
        <button
          class="view-toggle-btn"
          :class="{ active: viewMode === 'card' }"
          title="卡片视图"
          @click="setViewMode('card')"
        >
          ▦
        </button>
        <button
          class="view-toggle-btn"
          :class="{ active: viewMode === 'list' }"
          title="列表视图"
          @click="setViewMode('list')"
        >
          ☰
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1.25rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.search-box {
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  transition: border-color var(--transition-fast);
}

.search-box:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.search-icon {
  font-size: 0.9rem;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: none;
  font-size: 0.9rem;
  font-family: inherit;
  color: var(--text-primary);
  outline: none;
}

.search-input::placeholder {
  color: var(--text-tertiary);
}

.search-clear {
  background: none;
  border: none;
  color: var(--text-tertiary);
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  flex-shrink: 0;
}

.search-clear:hover {
  color: var(--text-primary);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.toolbar-select {
  padding: 0.5rem 2rem 0.5rem 0.75rem;
  font-size: 0.85rem;
  font-family: inherit;
  font-weight: 500;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  outline: none;
  transition: border-color var(--transition-fast);
  appearance: auto;
}

.toolbar-select:focus {
  border-color: var(--color-primary);
}

.sort-order-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  font-size: 1rem;
  font-family: inherit;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.sort-order-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.view-toggle {
  display: flex;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.view-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  font-size: 0.9rem;
  font-family: inherit;
  color: var(--text-tertiary);
  background: var(--bg-primary);
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.view-toggle-btn + .view-toggle-btn {
  border-left: 1px solid var(--border-color);
}

.view-toggle-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.view-toggle-btn.active {
  background: var(--color-primary);
  color: white;
}

@media (max-width: 767px) {
  .toolbar {
    flex-direction: column;
    gap: 0.75rem;
    align-items: stretch;
  }

  .search-box {
    min-width: 100%;
  }

  .toolbar-actions {
    justify-content: space-between;
  }
}
</style>
