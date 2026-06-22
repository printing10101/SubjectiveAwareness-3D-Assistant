<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useKnowledgeStore } from '../stores/knowledgeStore.js'
import CategorySidebar from '../components/knowledge/CategorySidebar.vue'
import SearchToolbar from '../components/knowledge/SearchToolbar.vue'
import ActiveTags from '../components/knowledge/ActiveTags.vue'
import KnowledgeCard from '../components/knowledge/KnowledgeCard.vue'
import KnowledgeListItem from '../components/knowledge/KnowledgeListItem.vue'
import Pagination from '../components/knowledge/Pagination.vue'
import LoadingState from '../components/knowledge/LoadingState.vue'
import EmptyState from '../components/knowledge/EmptyState.vue'

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

function handleEntryClick(entry) {
  const id = entry.id || entry._id
  router.push({ name: 'knowledgeDetail', params: { id } })
}

function handleCreateNew() {
  router.push({ name: 'knowledgeNew' })
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
      <CategorySidebar
        :selected-category="selectedCategory"
        :available-tags="availableTags"
        :selected-tags="selectedTags"
        :total="store.total"
        :is-mobile="isMobile"
        :class="{ 'drawer-open': isMobileDrawerOpen }"
        @select-category="selectCategory"
        @toggle-tag="toggleTag"
        @close-drawer="closeMobileDrawer"
      />

      <!-- 右侧内容区域 -->
      <main class="content-area">
        <!-- 搜索和工具栏 -->
        <SearchToolbar
          v-model:search-keyword="searchKeyword"
          v-model:sort-by="sortBy"
          :sort-order="sortOrder"
          :view-mode="viewMode"
          @toggle-sort-order="toggleSortOrder"
          @set-view-mode="setViewMode"
        />

        <!-- 已选标签展示 -->
        <ActiveTags
          :selected-tags="selectedTags"
          @remove-tag="removeTag"
        />

        <!-- 加载状态 -->
        <LoadingState v-if="store.loading" />

        <!-- 空状态 -->
        <EmptyState
          v-else-if="store.entries.length === 0"
          :has-filters="!!(searchKeyword || selectedCategory || selectedTags.length > 0)"
        />

        <!-- 卡片视图 -->
        <div
          v-else-if="viewMode === 'card'"
          class="card-grid"
        >
          <KnowledgeCard
            v-for="entry in store.entries"
            :key="entry.id || entry._id"
            :entry="entry"
            @click="handleEntryClick"
          />
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
          <KnowledgeListItem
            v-for="entry in store.entries"
            :key="entry.id || entry._id"
            :entry="entry"
            @click="handleEntryClick"
          />
        </div>

        <!-- 分页 -->
        <Pagination
          v-if="totalPages > 1 && store.entries.length > 0"
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total-pages="totalPages"
          :total="store.total"
        />
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

.knowledge-layout {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

.content-area {
  flex: 1;
  min-width: 0;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

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

.list-col {
  flex-shrink: 0;
}

.list-col--title {
  flex: 1;
  min-width: 0;
}

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
}

@media (min-width: 768px) and (max-width: 1023px) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  }
}
</style>