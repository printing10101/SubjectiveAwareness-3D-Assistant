<script setup>
import { ref, computed, onMounted } from 'vue'

import axios from 'axios'
import { marked } from 'marked'
import { useRoute, useRouter } from 'vue-router'

import { useKnowledgeStore } from '../stores/knowledgeStore.js'
import { isAuthenticated, isAdmin } from '../utils/auth.js'

const route = useRoute()
const router = useRouter()
const store = useKnowledgeStore()

const isLoading = ref(true)
const loadError = ref(null)
const relatedEntries = ref([])
const isDeleteConfirmVisible = ref(false)
const isDeleting = ref(false)

const entryId = computed(() => route.params.id)

const canEdit = computed(() => isAuthenticated())
const canDelete = computed(() => isAuthenticated() || isAdmin())

const renderedContent = computed(() => {
  if (!store.currentEntry || !store.currentEntry.content) return ''
  try {
    return marked(store.currentEntry.content, {
      breaks: true,
      gfm: true,
    })
  } catch {
    return store.currentEntry.content
  }
})

const confidencePercent = computed(() => {
  if (!store.currentEntry) return 0
  return Math.round((store.currentEntry.confidence_score || 0) * 100)
})

const categoryLabel = computed(() => {
  const cat = store.currentEntry?.category
  if (!cat) return '未分类'
  const map = {
    legal_provision: '法律条文',
    analysis_method: '分析方法',
    historical_case: '历史案例',
    criminal_law: '刑法',
    criminal_procedure_law: '刑事诉讼法',
    judicial_interpretation: '司法解释',
    evidence_analysis: '证据分析方法',
    legal_reasoning: '法律推理方法',
    case_comparison: '案例比较方法',
    precedent_case: '判例',
    typical_case: '典型案例',
    reference_case: '参考案例',
  }
  return map[cat] || cat
})

const statusLabel = computed(() => {
  const s = store.currentEntry?.status
  if (s === 'published') return '已审核'
  if (s === 'draft') return '草稿'
  if (s === 'review') return '审核中'
  return s || '草稿'
})

const statusClass = computed(() => {
  const s = store.currentEntry?.status
  return `status-${  s || 'draft'}`
})

function formatTime(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return dateStr
  }
}

function handleGoBack() {
  router.push({ name: 'knowledge' })
}

function handleEdit() {
  router.push({ name: 'knowledgeEdit', params: { id: entryId.value } })
}

function handleConfirmDelete() {
  isDeleteConfirmVisible.value = true
}

function handleCancelDelete() {
  isDeleteConfirmVisible.value = false
}

async function handleExecuteDelete() {
  isDeleting.value = true
  try {
    await store.deleteEntry(entryId.value)
    router.push({ name: 'knowledge' })
  } catch {
    isDeleteConfirmVisible.value = false
  } finally {
    isDeleting.value = false
  }
}

function handleRelatedClick(entry) {
  const id = entry.id || entry._id
  router.push({ name: 'knowledgeDetail', params: { id } })
}

function getConfidenceStars(score) {
  const s = Math.round((score || 0) * 5)
  return '★'.repeat(s) + '☆'.repeat(5 - s)
}

async function fetchRelatedEntries() {
  if (!store.currentEntry) return
  try {
    const response = await axios.get('/api/knowledge', {
      params: {
        category: store.currentEntry.category,
        page_size: 4,
        exclude: entryId.value,
      },
    })
    relatedEntries.value = (response.data.entries || response.data.items || [])
      .filter((e) => (e.id || e._id) !== entryId.value)
      .slice(0, 4)
  } catch {
    relatedEntries.value = []
  }
}

onMounted(async () => {
  isLoading.value = true
  loadError.value = null
  try {
    await store.fetchEntry(entryId.value)
    await fetchRelatedEntries()
  } catch (err) {
    loadError.value = err?.message || '加载知识条目失败'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div class="detail-page">
    <!-- 加载状态 -->
    <div
      v-if="isLoading"
      class="loading-area"
    >
      <div class="loading-spinner"></div>
      <p>正在加载知识条目...</p>
    </div>

    <!-- 错误状态 -->
    <div
      v-else-if="loadError"
      class="error-area"
    >
      <div class="error-card card">
        <div class="error-icon-large">⚠️</div>
        <h2 class="error-title">加载失败</h2>
        <p class="error-desc">{{ loadError }}</p>
        <div class="error-actions">
          <button
            class="btn btn-secondary"
            @click="handleGoBack"
          >
            返回列表
          </button>
          <button
            class="btn btn-primary"
            @click="router.go(0)"
          >
            重新加载
          </button>
        </div>
      </div>
    </div>

    <!-- 详情内容 -->
    <template v-else-if="store.currentEntry">
      <!-- 顶部操作栏 -->
      <div class="top-bar">
        <button
          class="back-btn"
          @click="handleGoBack"
        >
          <span class="back-arrow">←</span>
          返回列表
        </button>

        <div class="top-bar-actions">
          <button
            v-if="canEdit"
            class="btn btn-secondary btn-sm"
            @click="handleEdit"
          >
            编辑
          </button>
          <button
            v-if="canDelete"
            class="btn btn-danger btn-sm"
            @click="handleConfirmDelete"
          >
            删除
          </button>
        </div>
      </div>

      <!-- 信息头部 -->
      <div class="info-header card">
        <h1 class="entry-title">{{ store.currentEntry.title }}</h1>

        <div class="info-meta">
          <div class="meta-item">
            <span class="meta-label">分类</span>
            <span class="meta-value meta-category">{{ categoryLabel }}</span>
          </div>

          <div class="meta-item">
            <span class="meta-label">状态</span>
            <span
              class="status-badge"
              :class="statusClass"
            >
              {{ statusLabel }}
            </span>
          </div>

          <div class="meta-item">
            <span class="meta-label">信心评分</span>
            <div class="confidence-display">
              <div class="confidence-stars">
                {{ getConfidenceStars(store.currentEntry.confidence_score) }}
              </div>
              <div class="confidence-bar-wrapper">
                <div
                  class="confidence-bar-fill"
                  :style="{ width: confidencePercent + '%' }"
                ></div>
              </div>
              <span class="confidence-text">{{ confidencePercent }}%</span>
            </div>
          </div>

          <div class="meta-item">
            <span class="meta-label">创建时间</span>
            <span class="meta-value">{{ formatTime(store.currentEntry.created_at) }}</span>
          </div>

          <div class="meta-item">
            <span class="meta-label">更新时间</span>
            <span class="meta-value">{{ formatTime(store.currentEntry.updated_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 正文内容 -->
      <div class="content-section card">
        <h2 class="section-title">正文内容</h2>
        <div
          class="markdown-body"
          v-html="renderedContent"
        ></div>
      </div>

      <!-- 标签展示 -->
      <div
        v-if="store.currentEntry.tags && store.currentEntry.tags.length > 0"
        class="tags-section card"
      >
        <h2 class="section-title">标签</h2>
        <div class="tags-cloud">
          <span
            v-for="tag in store.currentEntry.tags"
            :key="tag"
            class="tag-cloud-item"
          >
            {{ tag }}
          </span>
        </div>
      </div>

      <!-- 关联条目 -->
      <div
        v-if="relatedEntries.length > 0"
        class="related-section"
      >
        <h2 class="section-title">相关知识条目</h2>
        <div class="related-grid">
          <div
            v-for="entry in relatedEntries"
            :key="entry.id || entry._id"
            class="related-card card"
            @click="handleRelatedClick(entry)"
          >
            <h3 class="related-title">{{ entry.title }}</h3>
            <p
              v-if="entry.summary"
              class="related-summary"
            >
              {{ entry.summary }}
            </p>
            <div class="related-meta">
              <span class="related-confidence">
                {{ getConfidenceStars(entry.confidence_score) }}
              </span>
              <span class="related-time">{{ formatTime(entry.updated_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 删除确认弹窗 -->
    <Teleport to="body">
      <div
        v-if="isDeleteConfirmVisible"
        class="dialog-overlay"
        @click.self="handleCancelDelete"
      >
        <div class="dialog dialog-sm card">
          <div class="dialog-header">
            <h2 class="dialog-title">确认删除</h2>
            <button
              class="dialog-close"
              @click="handleCancelDelete"
            >
              ×
            </button>
          </div>
          <div class="dialog-body">
            <p class="confirm-text">
              确定要删除此知识条目吗？此操作不可撤销。
            </p>
            <p
              v-if="store.currentEntry"
              class="confirm-target"
            >
              「{{ store.currentEntry.title }}」
            </p>
          </div>
          <div class="dialog-footer">
            <button
              class="btn btn-secondary"
              :disabled="isDeleting"
              @click="handleCancelDelete"
            >
              取消
            </button>
            <button
              class="btn btn-danger"
              :disabled="isDeleting"
              @click="handleExecuteDelete"
            >
              {{ isDeleting ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: var(--bg-secondary);
  padding: 2rem 1rem;
}

/* 加载状态 */
.loading-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 1rem;
  color: var(--text-secondary);
}

/* 错误状态 */
.error-area {
  display: flex;
  justify-content: center;
  padding-top: 4rem;
}

.error-card {
  max-width: 480px;
  width: 100%;
  text-align: center;
  padding: 3rem 2rem;
}

.error-icon-large {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.error-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.error-desc {
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
}

.error-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

/* 顶部操作栏 */
.top-bar {
  max-width: 900px;
  margin: 0 auto 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.9rem;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-secondary);
  background: none;
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.back-btn:hover {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
}

.back-arrow {
  font-size: 1.1rem;
}

.top-bar-actions {
  display: flex;
  gap: 0.5rem;
}

/* 信息头部 */
.info-header {
  max-width: 900px;
  margin: 0 auto 1.5rem;
  padding: 2rem;
}

.entry-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 1.5rem;
  line-height: 1.3;
}

.info-meta {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.meta-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-value {
  font-size: 0.9rem;
  color: var(--text-primary);
  font-weight: 500;
}

.meta-category {
  color: var(--color-primary);
}

.status-badge {
  display: inline-block;
  width: fit-content;
  padding: 0.2rem 0.625rem;
  font-size: 0.8rem;
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

/* 信心评分显示 */
.confidence-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.confidence-stars {
  font-size: 0.85rem;
  color: #eab308;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.confidence-bar-wrapper {
  flex: 1;
  max-width: 100px;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.confidence-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-warning), var(--color-success));
  border-radius: 3px;
  transition: width 0.5s ease;
}

.confidence-text {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
}

/* 正文内容 */
.content-section {
  max-width: 900px;
  margin: 0 auto 1.5rem;
  padding: 2rem;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--border-color);
}

/* Markdown 渲染样式 */
.markdown-body {
  font-size: 1rem;
  line-height: 1.8;
  color: var(--text-primary);
  word-wrap: break-word;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
}

.markdown-body :deep(h1) { font-size: 1.75rem; }
.markdown-body :deep(h2) { font-size: 1.5rem; }
.markdown-body :deep(h3) { font-size: 1.25rem; }
.markdown-body :deep(h4) { font-size: 1.1rem; }

.markdown-body :deep(p) {
  margin-bottom: 1rem;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-bottom: 1rem;
  padding-left: 1.5rem;
}

.markdown-body :deep(li) {
  margin-bottom: 0.25rem;
}

.markdown-body :deep(blockquote) {
  margin: 1rem 0;
  padding: 0.75rem 1rem;
  border-left: 4px solid var(--color-primary);
  background: var(--bg-secondary);
  border-radius: 0 var(--border-radius) var(--border-radius) 0;
  color: var(--text-secondary);
}

.markdown-body :deep(code) {
  padding: 0.2rem 0.4rem;
  font-size: 0.875rem;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
}

.markdown-body :deep(pre) {
  margin: 1rem 0;
  padding: 1rem;
  background: #1e293b;
  border-radius: var(--border-radius);
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: none;
  color: #e2e8f0;
  font-size: 0.85rem;
  line-height: 1.6;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--border-color);
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--bg-tertiary);
  font-weight: 600;
}

.markdown-body :deep(tr:nth-child(even)) {
  background: var(--bg-secondary);
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: var(--border-radius);
  margin: 1rem 0;
}

.markdown-body :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 1.5rem 0;
}

/* 标签云 */
.tags-section {
  max-width: 900px;
  margin: 0 auto 1.5rem;
  padding: 1.5rem 2rem;
}

.tags-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag-cloud-item {
  display: inline-block;
  padding: 0.375rem 0.875rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 100px;
  transition: all var(--transition-fast);
}

.tag-cloud-item:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.04);
}

/* 关联条目 */
.related-section {
  max-width: 900px;
  margin: 0 auto 1.5rem;
}

.related-section .section-title {
  margin-bottom: 1rem;
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.related-card {
  padding: 1.25rem;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.related-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.related-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.related-summary {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 0.75rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.related-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.related-confidence {
  font-size: 0.75rem;
  color: #eab308;
  letter-spacing: 0.05em;
}

.related-time {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

/* 删除确认弹窗 */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  z-index: 1000;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.dialog {
  width: 100%;
  max-width: 540px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 0;
  animation: slideUp 0.2s ease;
}

.dialog-sm {
  max-width: 420px;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.dialog-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.dialog-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
  transition: color var(--transition-fast);
}

.dialog-close:hover {
  color: var(--text-primary);
}

.dialog-body {
  padding: 1.5rem;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--border-color);
}

.confirm-text {
  font-size: 0.95rem;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.confirm-target {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-danger);
}

/* 响应式 */
@media (max-width: 767px) {
  .detail-page {
    padding: 1rem 0.75rem;
  }

  .entry-title {
    font-size: 1.375rem;
  }

  .info-header,
  .content-section,
  .tags-section {
    padding: 1.25rem;
  }

  .info-meta {
    grid-template-columns: 1fr 1fr;
  }

  .related-grid {
    grid-template-columns: 1fr;
  }

  .top-bar {
    flex-wrap: wrap;
  }
}
</style>