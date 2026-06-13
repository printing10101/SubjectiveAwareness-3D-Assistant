<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

import { useRouter } from 'vue-router'

import { useKnowledgeStore } from '../stores/knowledgeStore.js'

const router = useRouter()
const store = useKnowledgeStore()

const searchKeyword = ref('')
const selectedTags = ref([])
const selectedCategory = ref('')
const sortBy = ref('created_at')
const sortOrder = ref('desc')
const viewMode = ref('card')
const currentPage = ref(1)
const pageSize = ref(12)

const isMobileDrawerOpen = ref(false)
const isMobile = ref(false)

const categories = [
  { key: 'legal_provision', label: '法律条文' },
  { key: 'analysis_method', label: '分析方法' },
  { key: 'historical_case', label: '历史案例' },
]

const categoryTree = [
  {
    key: 'legal_provision',
    label: '法律条文',
    expanded: true,
    children: [
      { key: 'criminal_law', label: '刑法' },
      { key: 'criminal_procedure_law', label: '刑事诉讼法' },
      { key: 'judicial_interpretation', label: '司法解释' },
    ],
  },
  {
    key: 'analysis_method',
    label: '分析方法',
    expanded: true,
    children: [
      { key: 'evidence_analysis', label: '证据分析方法' },
      { key: 'legal_reasoning', label: '法律推理方法' },
      { key: 'case_comparison', label: '案例比较方法' },
    ],
  },
  {
    key: 'historical_case',
    label: '历史案例',
    expanded: false,
    children: [
      { key: 'precedent_case', label: '判例' },
      { key: 'typical_case', label: '典型案例' },
      { key: 'reference_case', label: '参考案例' },
    ],
  },
]

const sortOptions = [
  { value: 'created_at', label: '创建时间' },
  { value: 'updated_at', label: '更新时间' },
  { value: 'confidence_score', label: '信心评分' },
]

const pageSizeOptions = [8, 12, 20, 40]

const availableTags = computed(() => store.tags)

const totalPages = computed(() => Math.max(1, Math.ceil(store.total / pageSize.value)))

const queryParams = computed(() => ({
  page: currentPage.value,
  pageSize: pageSize.value,
  search: searchKeyword.value,
  tags: selectedTags.value,
  category: selectedCategory.value,
  sortBy: sortBy.value,
  sortOrder: sortOrder.value,
}))

watch(searchKeyword, () => {
  currentPage.value = 1
  fetchData()
})

watch(selectedCategory, () => {
  currentPage.value = 1
  fetchData()
})

watch([sortBy, sortOrder, pageSize], () => {
  currentPage.value = 1
  fetchData()
})

watch(currentPage, () => {
  fetchData()
})

function toggleCategoryExpand(cat) {
  cat.expanded = !cat.expanded
}

function selectCategory(key) {
  selectedCategory.value = selectedCategory.value === key ? '' : key
}

function toggleTag(tag) {
  const index = selectedTags.value.indexOf(tag)
  if (index === -1) {
    selectedTags.value.push(tag)
  } else {
    selectedTags.value.splice(index, 1)
  }
  currentPage.value = 1
  fetchData()
}

function removeTag(tag) {
  const index = selectedTags.value.indexOf(tag)
  if (index !== -1) {
    selectedTags.value.splice(index, 1)
    currentPage.value = 1
    fetchData()
  }
}

function toggleSortOrder() {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
}

function setViewMode(mode) {
  viewMode.value = mode
}

function goToPage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  currentPage.value = page
}

function getPaginationPages() {
  const pages = []
  const tp = totalPages.value
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (currentPage.value > 3) pages.push('...')
    const start = Math.max(2, currentPage.value - 1)
    const end = Math.min(tp - 1, currentPage.value + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (currentPage.value < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
}

function handleEntryClick(entry) {
  const id = entry.id || entry._id
  router.push({ name: 'knowledgeDetail', params: { id } })
}

function handleCreateNew() {
  router.push({ name: 'knowledgeNew' })
}

function formatTime(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  } catch {
    return dateStr
  }
}

function getCategoryLabel(key) {
  const found = categories.find((c) => c.key === key)
  if (found) return found.label
  for (const cat of categoryTree) {
    if (cat.key === key) return cat.label
    for (const child of cat.children) {
      if (child.key === key) return child.label
    }
  }
  return key || '未分类'
}

function getConfidenceStars(score) {
  const s = Math.round((score || 0) * 5)
  return '★'.repeat(s) + '☆'.repeat(5 - s)
}

function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

function toggleMobileDrawer() {
  isMobileDrawerOpen.value = !isMobileDrawerOpen.value
}

function closeMobileDrawer() {
  isMobileDrawerOpen.value = false
}

async function fetchData() {
  await store.fetchEntries(queryParams.value)
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  store.fetchTags()
  fetchData()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<template>
  <div class="knowledge-page">
    <header class="knowledge-header">
      <div class="header-left">
        <h1 class="page-title">知识库</h1>
        <p class="page-subtitle">浏览和管理法律知识条目</p>
      </div>
      <div class="header-right">
        <button
          class="btn btn-primary"
          @click="handleCreateNew"
        >
          <span class="btn-icon">+</span>
          新建知识
        </button>
        <button
          v-if="isMobile"
          class="drawer-toggle-btn"
          @click="toggleMobileDrawer"
        >
          <span class="drawer-toggle-icon">☰</span>
          分类
        </button>
      </div>
    </header>

    <div
      v-if="store.error"
      class="error-alert"
    >
      <span class="error-icon">!</span>
      <span class="error-text">{{ store.error }}</span>
      <button
        class="error-close"
        @click="store.clearError()"
      >
        ×
      </button>
    </div>

    <div class="knowledge-layout">
      <!-- 移动端遮罩 -->
      <div
        v-if="isMobile && isMobileDrawerOpen"
        class="drawer-overlay"
        @click="closeMobileDrawer"
      ></div>

      <!-- 左侧分类树 / 移动端抽屉 -->
      <aside
        class="category-sidebar card"
        :class="{ 'drawer-open': isMobileDrawerOpen }"
      >
        <div class="sidebar-header">
          <h3 class="sidebar-title">分类导航</h3>
          <button
            v-if="isMobile"
            class="sidebar-close"
            @click="closeMobileDrawer"
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
            <span class="category-count">{{ store.total }}</span>
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

        <!-- 标签筛选 -->
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

      <!-- 右侧内容区域 -->
      <main class="content-area">
        <!-- 搜索和工具栏 -->
        <div class="toolbar card">
          <div class="search-box">
            <span class="search-icon">🔍</span>
            <input
              v-model="searchKeyword"
              type="text"
              class="search-input"
              placeholder="搜索知识条目..."
            />
            <button
              v-if="searchKeyword"
              class="search-clear"
              @click="searchKeyword = ''"
            >
              ×
            </button>
          </div>

          <div class="toolbar-actions">
            <select
              v-model="sortBy"
              class="toolbar-select"
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

        <!-- 已选标签展示 -->
        <div
          v-if="selectedTags.length > 0"
          class="active-tags"
        >
          <span class="active-tags-label">已选标签：</span>
          <span
            v-for="tag in selectedTags"
            :key="tag"
            class="active-tag"
          >
            {{ tag }}
            <button
              class="active-tag-remove"
              @click="removeTag(tag)"
            >
              ×
            </button>
          </span>
        </div>

        <!-- 加载状态 -->
        <div
          v-if="store.loading"
          class="loading-area card"
        >
          <div class="loading-spinner"></div>
          <p>正在加载知识条目...</p>
        </div>

        <!-- 空状态 -->
        <div
          v-else-if="store.entries.length === 0"
          class="empty-area card"
        >
          <div class="empty-icon">📖</div>
          <h3 class="empty-title">暂无知识条目</h3>
          <p class="empty-desc">
            {{
              searchKeyword || selectedCategory || selectedTags.length > 0
                ? '没有匹配的知识条目，请调整筛选条件'
                : '点击上方"新建知识"按钮创建第一个知识条目'
            }}
          </p>
        </div>

        <!-- 卡片视图 -->
        <div
          v-else-if="viewMode === 'card'"
          class="card-grid"
        >
          <div
            v-for="entry in store.entries"
            :key="entry.id || entry._id"
            class="knowledge-card card"
            @click="handleEntryClick(entry)"
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
        </div>

        <!-- 列表视图 -->
        <div
          v-else
          class="list-wrapper card"
        >
          <div class="list-header">
            <span class="list-col list-col--title">标题</span>
            <span class="list-col list-col--category">分类</span>
            <span class="list-col list-col--status">状态</span>
            <span class="list-col list-col--confidence">信心评分</span>
            <span class="list-col list-col--time">更新时间</span>
          </div>
          <div
            v-for="entry in store.entries"
            :key="entry.id || entry._id"
            class="list-row"
            @click="handleEntryClick(entry)"
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
        </div>

        <!-- 分页 -->
        <div
          v-if="totalPages > 1 && store.entries.length > 0"
          class="pagination"
        >
          <div class="pagination-left">
            <span class="page-info">共 {{ store.total }} 条</span>
            <select
              v-model="pageSize"
              class="page-size-select"
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
      </main>
    </div>
  </div>
</template>

<style scoped>
.knowledge-page {
  min-height: 100vh;
  background: var(--bg-secondary);
  padding: 2rem 1rem;
}

.knowledge-header {
  max-width: 1400px;
  margin: 0 auto 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.header-left {
  flex: 1;
}

.header-right {
  display: flex;
  gap: 0.75rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.page-subtitle {
  color: var(--text-secondary);
  font-size: 1rem;
}

.btn-icon {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1;
}

.drawer-toggle-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.625rem 1rem;
  font-size: 0.9rem;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-secondary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.drawer-toggle-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.drawer-toggle-icon {
  font-size: 1.125rem;
}

.error-alert {
  max-width: 1400px;
  margin: 0 auto 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--border-radius);
  animation: shake 0.3s ease;
}

.error-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: var(--color-danger);
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.error-text {
  flex: 1;
  color: #991b1b;
  font-size: 0.9rem;
}

.error-close {
  background: none;
  border: none;
  color: #991b1b;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

/* 主体布局 */
.knowledge-layout {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

/* 分类侧边栏 */
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

/* 内容区域 */
.content-area {
  flex: 1;
  min-width: 0;
}

/* 工具栏 */
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

/* 已选标签 */
.active-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  margin-bottom: 1rem;
  padding: 0.5rem 0;
}

.active-tags-label {
  font-size: 0.8rem;
  color: var(--text-tertiary);
  font-weight: 500;
}

.active-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem 0.25rem 0.625rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  border: 1px solid rgba(79, 70, 229, 0.2);
  border-radius: 100px;
}

.active-tag-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  font-size: 0.75rem;
  font-family: inherit;
  color: var(--color-primary);
  background: none;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.active-tag-remove:hover {
  background: rgba(79, 70, 229, 0.2);
}

/* 加载状态 */
.loading-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  gap: 1rem;
  color: var(--text-secondary);
}

/* 空状态 */
.empty-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-desc {
  color: var(--text-secondary);
  font-size: 0.9rem;
  max-width: 360px;
}

/* 卡片视图 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

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

/* 列表视图 */
.list-wrapper {
  padding: 0;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  padding: 0.75rem 1.25rem;
  background: var(--bg-tertiary);
  border-bottom: 2px solid var(--border-color);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
}

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

/* 分页 */
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

/* 移动端适配 */
.drawer-overlay {
  display: none;
}

@media (max-width: 767px) {
  .knowledge-page {
    padding: 1rem 0.75rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .header-right {
    width: 100%;
  }

  .header-right .btn {
    flex: 1;
  }

  .knowledge-layout {
    flex-direction: column;
  }

  .category-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 280px;
    height: 100vh;
    z-index: 200;
    border-radius: 0;
    max-height: none;
    transform: translateX(-100%);
    transition: transform var(--transition-normal);
    box-shadow: var(--shadow-lg);
  }

  .category-sidebar.drawer-open {
    transform: translateX(0);
  }

  .sidebar-close {
    display: block;
  }

  .drawer-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 199;
    animation: fadeIn 0.2s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .card-grid {
    grid-template-columns: 1fr;
  }

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

  .list-header,
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

  .pagination {
    flex-direction: column;
    gap: 0.75rem;
  }
}

@media (min-width: 768px) and (max-width: 1023px) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  }
}
</style>