<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

import axios from 'axios'
import { useRouter } from 'vue-router'

import KnowledgeGraph from '../components/KnowledgeGraph.vue'

const router = useRouter()

const graphRef = ref(null)
const loading = ref(false)
const error = ref(null)
const nodes = ref([])
const edges = ref([])
const allTags = ref([])

const searchQuery = ref('')
const debouncedSearch = ref('')
const showEdgeLabels = ref(false)
const selectedCategories = ref([])
const selectedTags = ref([])
const selectedRelationTypes = ref([])
const isFilterPanelOpen = ref(false)
const isMobile = ref(false)
const highlightedNodes = ref([])
const stats = ref({ nodeCount: 0, edgeCount: 0 })

let searchTimer = null

const CATEGORY_META = {
  law: { label: '法律条文', color: '#4F46E5' },
  methodology: { label: '分析方法', color: '#059669' },
  case: { label: '案例', color: '#D97706' },
  other: { label: '其他', color: '#6B7280' },
}

const RELATION_LINE_STYLE_META = {
  references: { label: '引用', lineStyle: 'solid', color: '#9CA3AF' },
  contradicts: { label: '矛盾', lineStyle: 'dashed', color: '#EF4444' },
  supersedes: { label: '取代', lineStyle: 'dotted', color: '#F59E0B' },
  extends: { label: '扩展', lineStyle: 'solid', color: '#10B981' },
  depends_on: { label: '依赖', lineStyle: 'dashed', color: '#3B82F6' },
}

const categoryFilters = computed(() => Object.keys(CATEGORY_META))
const relationTypeFilters = computed(() => Object.keys(RELATION_LINE_STYLE_META))

const hasActiveFilters = computed(
  () =>
    selectedCategories.value.length > 0 ||
    selectedTags.value.length > 0 ||
    selectedRelationTypes.value.length > 0 ||
    debouncedSearch.value !== ''
)

watch(searchQuery, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    debouncedSearch.value = val
  }, 300)
})

watch([debouncedSearch, selectedCategories, selectedTags, selectedRelationTypes], () => {
  fetchGraphData()
})

function toggleCategory(cat) {
  const idx = selectedCategories.value.indexOf(cat)
  if (idx === -1) {
    selectedCategories.value.push(cat)
  } else {
    selectedCategories.value.splice(idx, 1)
  }
}

function toggleTag(tag) {
  const idx = selectedTags.value.indexOf(tag)
  if (idx === -1) {
    selectedTags.value.push(tag)
  } else {
    selectedTags.value.splice(idx, 1)
  }
}

function toggleRelationType(rt) {
  const idx = selectedRelationTypes.value.indexOf(rt)
  if (idx === -1) {
    selectedRelationTypes.value.push(rt)
  } else {
    selectedRelationTypes.value.splice(idx, 1)
  }
}

function clearFilters() {
  selectedCategories.value = []
  selectedTags.value = []
  selectedRelationTypes.value = []
  searchQuery.value = ''
  debouncedSearch.value = ''
}

function toggleFilterPanel() {
  isFilterPanelOpen.value = !isFilterPanelOpen.value
}

function handleNodeClick(node) {
  router.push({ name: 'knowledgeDetail', params: { id: node.id } })
}

function handleGraphReady() {
  updateStats()
}

function updateStats() {
  stats.value = {
    nodeCount: nodes.value.length,
    edgeCount: edges.value.length,
  }
}

async function fetchGraphData() {
  loading.value = true
  error.value = null
  try {
    const params = {}
    if (selectedCategories.value.length) params.category = selectedCategories.value
    if (selectedTags.value.length) params.tag = selectedTags.value
    if (selectedRelationTypes.value.length) params.relationType = selectedRelationTypes.value
    if (debouncedSearch.value) params.search = debouncedSearch.value

    const res = await axios.get('/api/knowledge/graph', {
      params,
      paramsSerializer: { indexes: null },
    })
    nodes.value = res.data.nodes || []
    edges.value = res.data.edges || []
    updateStats()

    if (debouncedSearch.value) {
      const searchLower = debouncedSearch.value.toLowerCase()
      const matchedIds = nodes.value
        .filter((n) => (n.label || '').toLowerCase().includes(searchLower))
        .map((n) => n.id)
      highlightedNodes.value = matchedIds
      if (matchedIds.length > 0 && graphRef.value) {
        setTimeout(() => {
          graphRef.value.centerOnNode(matchedIds[0])
        }, 500)
      }
    } else {
      highlightedNodes.value = []
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || '加载图谱数据失败'
  } finally {
    loading.value = false
  }
}

async function fetchTags() {
  try {
    const res = await axios.get('/api/knowledge/tags')
    allTags.value = res.data || []
  } catch {
    allTags.value = []
  }
}

function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  fetchGraphData()
  fetchTags()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <div class="graph-view-page">
    <header class="graph-header">
      <div class="header-left">
        <h1 class="page-title">知识图谱</h1>
        <p class="page-subtitle">
          可视化浏览知识条目之间的关联关系
          <span v-if="stats.nodeCount" class="graph-stats-badge">
            {{ stats.nodeCount }} 节点 · {{ stats.edgeCount }} 边
          </span>
        </p>
      </div>
      <div class="header-right">
        <button
          v-if="isMobile"
          class="btn btn-secondary"
          @click="toggleFilterPanel"
        >
          <span>☰</span> 筛选
        </button>
      </div>
    </header>

    <div class="graph-layout">
      <aside
        class="filter-sidebar"
        :class="{ 'filter-open': isFilterPanelOpen }"
      >
        <div class="filter-sidebar-header">
          <h3 class="filter-title">筛选面板</h3>
          <button
            v-if="isMobile"
            class="filter-close-btn"
            @click="isFilterPanelOpen = false"
          >×</button>
        </div>

        <div class="search-section">
          <div class="search-box">
            <span class="search-icon">🔍</span>
            <input
              v-model="searchQuery"
              type="text"
              class="search-input"
              placeholder="搜索知识条目..."
            />
            <button
              v-if="searchQuery"
              class="search-clear"
              @click="searchQuery = ''"
            >×</button>
          </div>
        </div>

        <div class="filter-section">
          <h4 class="filter-section-title">分类筛选</h4>
          <div class="filter-list">
            <button
              v-for="cat in categoryFilters"
              :key="cat"
              class="filter-chip"
              :class="{ active: selectedCategories.includes(cat) }"
              :style="selectedCategories.includes(cat) ? { borderColor: CATEGORY_META[cat].color, color: CATEGORY_META[cat].color, background: CATEGORY_META[cat].color + '15' } : {}"
              @click="toggleCategory(cat)"
            >
              <span
                class="filter-chip-dot"
                :style="{ background: CATEGORY_META[cat].color }"
              ></span>
              {{ CATEGORY_META[cat].label }}
            </button>
          </div>
        </div>

        <div v-if="allTags.length" class="filter-section">
          <h4 class="filter-section-title">标签筛选</h4>
          <div class="filter-list">
            <button
              v-for="tag in allTags"
              :key="tag.id"
              class="filter-chip filter-chip--tag"
              :class="{ active: selectedTags.includes(tag.name) }"
              :style="tag.color ? { '--tag-color': tag.color } : {}"
              @click="toggleTag(tag.name)"
            >
              {{ tag.name }}
            </button>
          </div>
        </div>

        <div class="filter-section">
          <h4 class="filter-section-title">关系类型筛选</h4>
          <div class="filter-list">
            <button
              v-for="rt in relationTypeFilters"
              :key="rt"
              class="filter-chip filter-chip--relation"
              :class="{ active: selectedRelationTypes.includes(rt) }"
              :style="selectedRelationTypes.includes(rt) ? { borderColor: RELATION_LINE_STYLE_META[rt].color } : {}"
              @click="toggleRelationType(rt)"
            >
              <svg width="24" height="10" class="filter-chip-line">
                <line
                  x1="2"
                  y1="5"
                  x2="22"
                  y2="5"
                  :stroke="RELATION_LINE_STYLE_META[rt].color"
                  stroke-width="2"
                  :stroke-dasharray="RELATION_LINE_STYLE_META[rt].lineStyle === 'dashed' ? '4,3' : RELATION_LINE_STYLE_META[rt].lineStyle === 'dotted' ? '1,3' : 'none'"
                />
              </svg>
              {{ RELATION_LINE_STYLE_META[rt].label }}
            </button>
          </div>
        </div>

        <div class="filter-section">
          <label class="toggle-label">
            <input v-model="showEdgeLabels" type="checkbox" class="toggle-input" />
            <span class="toggle-text">显示关系标签</span>
          </label>
        </div>

        <button
          v-if="hasActiveFilters"
          class="btn btn-secondary clear-btn"
          @click="clearFilters"
        >
          清除所有筛选
        </button>

        <div v-if="isMobile && isFilterPanelOpen" class="filter-overlay" @click="isFilterPanelOpen = false"></div>
      </aside>

      <main class="graph-main">
        <div v-if="error && !nodes.length" class="error-banner">
          <span class="error-banner-icon">!</span>
          <span>{{ error }}</span>
          <button class="error-banner-close" @click="error = null">×</button>
        </div>

        <KnowledgeGraph
          ref="graphRef"
          :nodes="nodes"
          :edges="edges"
          mode="full"
          :loading="loading"
          :error="error && !nodes.length ? error : null"
          :show-edge-labels="showEdgeLabels"
          :highlighted-node-ids="highlightedNodes"
          :on-node-click="handleNodeClick"
          @ready="handleGraphReady"
        />

        <div class="graph-legend">
          <div class="legend-group">
            <span class="legend-group-title">分类颜色：</span>
            <span
              v-for="cat in categoryFilters"
              :key="cat"
              class="legend-item"
            >
              <span class="legend-dot" :style="{ background: CATEGORY_META[cat].color }"></span>
              {{ CATEGORY_META[cat].label }}
            </span>
          </div>
          <div class="legend-group">
            <span class="legend-group-title">关系线型：</span>
            <span
              v-for="rt in relationTypeFilters"
              :key="rt"
              class="legend-item"
            >
              <svg width="28" height="12" class="legend-line-svg">
                <line
                  x1="2"
                  y1="6"
                  x2="26"
                  y2="6"
                  :stroke="RELATION_LINE_STYLE_META[rt].color"
                  stroke-width="2"
                  :stroke-dasharray="RELATION_LINE_STYLE_META[rt].lineStyle === 'dashed' ? '4,3' : RELATION_LINE_STYLE_META[rt].lineStyle === 'dotted' ? '1,3' : 'none'"
                />
              </svg>
              {{ RELATION_LINE_STYLE_META[rt].label }}
            </span>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.graph-view-page {
  min-height: 100vh;
  background: var(--bg-secondary, #f9fafb);
  display: flex;
  flex-direction: column;
}

.graph-header {
  padding: 1.5rem 1.5rem 0;
  display: flex;
  align-items: flex-start;
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
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary, #111827);
  margin-bottom: 0.25rem;
}

.page-subtitle {
  color: var(--text-secondary, #6b7280);
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.graph-stats-badge {
  font-size: 0.8rem;
  background: var(--bg-tertiary, #f3f4f6);
  color: var(--text-secondary, #6b7280);
  padding: 0.15rem 0.6rem;
  border-radius: 100px;
  font-weight: 500;
}

.graph-layout {
  flex: 1;
  display: flex;
  gap: 0;
  padding: 1rem 1.5rem 1.5rem;
  min-height: 0;
}

.filter-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-right: 1rem;
  overflow-y: auto;
}

.filter-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #111827);
}

.filter-close-btn {
  display: none;
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-tertiary, #9ca3af);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.search-section {
  margin-bottom: 0.25rem;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary, #ffffff);
  border: 2px solid var(--border-color, #d1d5db);
  border-radius: var(--border-radius, 8px);
  transition: border-color 0.15s ease;
}

.search-box:focus-within {
  border-color: var(--color-primary, #4F46E5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.search-icon {
  font-size: 0.85rem;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: none;
  font-size: 0.85rem;
  font-family: inherit;
  color: var(--text-primary, #111827);
  outline: none;
}

.search-input::placeholder {
  color: var(--text-tertiary, #9ca3af);
}

.search-clear {
  background: none;
  border: none;
  color: var(--text-tertiary, #9ca3af);
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.filter-section {
  border-top: 1px solid var(--border-color, #e5e7eb);
  padding-top: 0.875rem;
}

.filter-section-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.filter-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.filter-chip {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.3rem 0.625rem;
  font-size: 0.8rem;
  font-family: inherit;
  font-weight: 500;
  color: var(--text-secondary, #6b7280);
  background: var(--bg-primary, #ffffff);
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 100px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-chip:hover {
  border-color: var(--color-primary, #4F46E5);
}

.filter-chip.active {
  background: rgba(79, 70, 229, 0.08);
  border-color: var(--color-primary, #4F46E5);
  color: var(--color-primary, #4F46E5);
}

.filter-chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.filter-chip-line {
  flex-shrink: 0;
}

.filter-chip--tag.active {
  border-color: var(--tag-color, #4F46E5);
  color: var(--tag-color, #4F46E5);
  background: color-mix(in srgb, var(--tag-color, #4F46E5) 10%, transparent);
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--text-secondary, #6b7280);
}

.toggle-input {
  accent-color: var(--color-primary, #4F46E5);
  width: 16px;
  height: 16px;
}

.toggle-text {
  user-select: none;
}

.clear-btn {
  width: 100%;
  font-size: 0.8rem;
  justify-content: center;
}

.graph-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 0.75rem;
  min-height: 500px;
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--border-radius, 8px);
  color: #991b1b;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.error-banner-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: #dc2626;
  color: white;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.error-banner-close {
  margin-left: auto;
  background: none;
  border: none;
  color: #991b1b;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  font-weight: 500;
  font-family: inherit;
  border-radius: var(--border-radius, 8px);
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid var(--border-color, #d1d5db);
}

.btn-secondary {
  background: var(--bg-primary, #ffffff);
  color: var(--text-secondary, #6b7280);
}

.btn-secondary:hover {
  border-color: var(--color-primary, #4F46E5);
  color: var(--color-primary, #4F46E5);
}

.graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  padding: 0.625rem 0;
  flex-shrink: 0;
  font-size: 0.75rem;
  color: var(--text-tertiary, #9ca3af);
}

.legend-group {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex-wrap: wrap;
}

.legend-group-title {
  font-weight: 600;
  color: var(--text-secondary, #6b7280);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-line-svg {
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .graph-view-page {
    padding: 0;
  }

  .graph-header {
    padding: 1rem 0.75rem 0;
  }

  .page-title {
    font-size: 1.35rem;
  }

  .graph-layout {
    flex-direction: column;
    padding: 0.75rem;
  }

  .filter-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 280px;
    height: 100vh;
    z-index: 200;
    background: var(--bg-primary, #ffffff);
    padding: 1.25rem;
    box-shadow: var(--shadow-lg, 0 10px 25px rgba(0,0,0,0.15));
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    overflow-y: auto;
  }

  .filter-sidebar.filter-open {
    transform: translateX(0);
  }

  .filter-close-btn {
    display: block;
  }

  .filter-overlay {
    display: none;
  }

  .graph-main {
    min-height: 60vh;
  }

  .graph-legend {
    gap: 1rem;
    font-size: 0.7rem;
  }
}

@media (min-width: 768px) and (max-width: 1023px) {
  .filter-sidebar {
    width: 220px;
  }
}
</style>