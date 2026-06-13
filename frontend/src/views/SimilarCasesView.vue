<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()

// 响应式数据
const caseDescription = ref('')
const isSearching = ref(false)
const searchError = ref(null)
const similarCases = ref([])
const maxChars = 5000

// 计算属性
const charCount = computed(() => caseDescription.value.length)
const isOverLimit = computed(() => charCount.value > maxChars)
const canSearch = computed(() => caseDescription.value.trim().length >= 10 && !isOverLimit.value && !isSearching.value)

// 方法
function handleClearInput() {
  caseDescription.value = ''
  searchError.value = null
  similarCases.value = []
}

async function handleSearch() {
  if (!canSearch.value) return

  isSearching.value = true
  searchError.value = null
  similarCases.value = []

  try {
    const response = await axios.post('/api/cases/similar', {
      description: caseDescription.value.trim(),
      top_k: 5,
    })

    similarCases.value = response.data.cases || []
  } catch (error) {
    searchError.value = error.response?.data?.detail || error.message || '检索失败，请稍后重试'
  } finally {
    isSearching.value = false
  }
}

function handleBackToHome() {
  router.push('/main')
}

function getSimilarityColor(score) {
  if (score >= 0.8) return '#22c55e'
  if (score >= 0.6) return '#eab308'
  return '#94a3b8'
}

function getVerdictBadgeClass(verdict) {
  if (verdict === '有罪') return 'badge-guilty'
  if (verdict === '无罪') return 'badge-not-guilty'
  return 'badge-pending'
}
</script>

<template>
  <div class="similar-cases-page">
    <div class="container">
      <div class="page-header">
        <button
          class="back-btn"
          @click="handleBackToHome"
        >
          ← 返回
        </button>
        <h1 class="page-title">相似案例检索</h1>
        <p class="page-subtitle">输入案情描述，查找相似历史案例</p>
      </div>

      <div class="search-section">
        <div class="input-wrapper">
          <label
            class="input-label"
            for="case-desc"
          >案情描述</label>
          <div class="char-count">
            <span :class="{ 'over-limit': isOverLimit }">{{ charCount }}</span>
            / {{ maxChars }}
          </div>
        </div>

        <textarea
          id="case-desc"
          v-model="caseDescription"
          class="case-textarea"
          placeholder="请详细描述案件情况，包括交易方式、金额、时间、嫌疑人行为等关键信息..."
          rows="10"
          :class="{ 'over-limit': isOverLimit }"
        ></textarea>

        <div
          v-if="searchError"
          class="error-message"
        >
          <span class="error-icon">⚠️</span>
          <span>{{ searchError }}</span>
        </div>

        <div class="action-buttons">
          <button
            class="btn btn-secondary"
            :disabled="!caseDescription.trim()"
            @click="handleClearInput"
          >
            清除输入
          </button>
          <button
            class="btn btn-primary"
            :disabled="!canSearch"
            @click="handleSearch"
          >
            <template v-if="isSearching">
              <span class="btn-spinner"></span>
              检索中...
            </template>
            <template v-else>
              🔍 开始检索
            </template>
          </button>
        </div>
      </div>

      <div
        v-if="similarCases.length > 0"
        class="results-section"
      >
        <h2 class="section-title">
          相似案例 ({{ similarCases.length }})
        </h2>
        <div class="cases-grid">
          <div
            v-for="(caseItem, index) in similarCases"
            :key="index"
            class="case-card"
          >
            <div class="case-header">
              <div class="case-rank">
                #{{ index + 1 }}
              </div>
              <div
                class="similarity-score"
                :style="{ color: getSimilarityColor(caseItem.similarity) }"
              >
                相似度: {{ (caseItem.similarity * 100).toFixed(1) }}%
              </div>
            </div>

            <div class="case-body">
              <div class="case-info-row">
                <span class="info-label">档级:</span>
                <span class="info-value">
                  D1: {{ caseItem.d1 || '-' }} / D2: {{ caseItem.d2 || '-' }} / D3: {{ caseItem.d3 || '-' }}
                </span>
              </div>

              <div class="case-info-row">
                <span class="info-label">判决结果:</span>
                <span
                  class="verdict-badge"
                  :class="getVerdictBadgeClass(caseItem.verdict)"
                >
                  {{ caseItem.verdict || '未知' }}
                </span>
              </div>

              <div
                v-if="caseItem.sentence"
                class="case-info-row"
              >
                <span class="info-label">量刑:</span>
                <span class="info-value">{{ caseItem.sentence }}</span>
              </div>

              <div
                v-if="caseItem.fine"
                class="case-info-row"
              >
                <span class="info-label">罚金:</span>
                <span class="info-value">{{ caseItem.fine }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        v-else-if="!isSearching && caseDescription.trim().length > 0 && similarCases.length === 0"
        class="empty-state"
      >
        <div class="empty-icon">📚</div>
        <p class="empty-text">暂无检索结果，请调整案情描述后重试</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.similar-cases-page {
  min-height: 100vh;
  padding: 2rem 0;
  background: var(--bg-secondary);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.page-header {
  margin-bottom: 2rem;
}

.back-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0;
  margin-bottom: 1rem;
}

.back-btn:hover {
  text-decoration: underline;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.5rem;
}

.page-subtitle {
  font-size: 0.9375rem;
  color: var(--text-secondary);
  margin: 0;
}

.search-section {
  background: white;
  border-radius: var(--border-radius-lg);
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-sm);
}

.input-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.input-label {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.char-count {
  font-size: 0.875rem;
  color: var(--text-tertiary);
}

.char-count .over-limit {
  color: var(--color-danger);
  font-weight: 600;
}

.case-textarea {
  width: 100%;
  padding: 1rem;
  font-size: 0.9375rem;
  line-height: 1.6;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  resize: vertical;
  font-family: inherit;
  transition: border-color var(--transition-fast);
  box-sizing: border-box;
}

.case-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.case-textarea.over-limit {
  border-color: var(--color-danger);
}

.error-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: rgba(239, 68, 68, 0.06);
  color: var(--color-danger);
  border-radius: var(--border-radius);
  font-size: 0.875rem;
}

.error-icon {
  flex-shrink: 0;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.btn {
  padding: 0.625rem 1.25rem;
  border-radius: var(--border-radius);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #4338ca;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--border-color);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.results-section {
  margin-top: 2rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 1.5rem;
}

.cases-grid {
  display: grid;
  gap: 1.5rem;
}

.case-card {
  background: white;
  border-radius: var(--border-radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-fast);
}

.case-card:hover {
  box-shadow: var(--shadow-md);
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.case-rank {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary);
}

.similarity-score {
  font-size: 1rem;
  font-weight: 600;
}

.case-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.case-info-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9375rem;
}

.info-label {
  color: var(--text-secondary);
  font-weight: 500;
  min-width: 80px;
}

.info-value {
  color: var(--text-primary);
}

.verdict-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 600;
}

.badge-guilty {
  background: #fee2e2;
  color: #991b1b;
}

.badge-not-guilty {
  background: #dcfce7;
  color: #166534;
}

.badge-pending {
  background: #fef3c7;
  color: #92400e;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-sm);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-text {
  font-size: 1rem;
  color: var(--text-secondary);
  margin: 0;
}

@media (max-width: 768px) {
  .container {
    padding: 0 1rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .action-buttons {
    flex-direction: column;
  }

  .btn {
    width: 100%;
    justify-content: center;
  }

  .case-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>
