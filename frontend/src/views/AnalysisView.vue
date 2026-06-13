<script setup>
import { ref, computed, onMounted } from 'vue'

import axios from 'axios'
import { useRouter } from 'vue-router'

import AnalysisResult from '../components/analysis/AnalysisResult.vue'
import DimensionMatrix from '../components/analysis/DimensionMatrix.vue'
import RuleTransparency from '../components/analysis/RuleTransparency.vue'
import { useAnalysisStore } from '../stores/analysisStore.js'

const router = useRouter()
const analysisStore = useAnalysisStore()

const caseText = ref(analysisStore.currentCaseText || '')
const isSubmitting = ref(false)
const submitError = ref(null)
const responseTime = ref(null)

const hasMinimumText = computed(() => caseText.value.trim().length >= 10)

const textCharCount = computed(() => caseText.value.length)

const textWordCount = computed(() => {
  const text = caseText.value.trim()
  if (!text) return 0
  return text.split(/[\s\n]+/).filter(Boolean).length
})

function handleTextInput(event) {
  caseText.value = event.target.value
  analysisStore.setCaseText(caseText.value)
}

function handleClearText() {
  caseText.value = ''
  analysisStore.setCaseText('')
  submitError.value = null
}

function handleSubmit() {
  if (!hasMinimumText.value || isSubmitting.value) return

  isSubmitting.value = true
  submitError.value = null

  const startTime = Date.now()

  axios
    .post('/api/analyze', {
      case_text: caseText.value.trim(),
    })
    .then((res) => {
      const elapsed = Date.now() - startTime
      responseTime.value = elapsed
      analysisStore.setResponseTime(elapsed)

      const result = res.data
      analysisStore.setAnalysisResult(result)
      analysisStore.navigateToReport()

      router.push('/report')
    })
    .catch((err) => {
      submitError.value = err.response?.data?.detail || err.message || '分析请求失败，请稍后重试'
      analysisStore.setError(submitError.value)
    })
    .finally(() => {
      isSubmitting.value = false
    })
}

function handleRetry() {
  submitError.value = null
  analysisStore.clearError()
  handleSubmit()
}

function handleBackToDashboard() {
  router.push('/main')
}

onMounted(() => {
  if (analysisStore.currentCaseText) {
    caseText.value = analysisStore.currentCaseText
  }
})
</script>

<template>
  <div class="analysis-page">
    <div class="container">
      <div class="page-header">
        <button
          class="back-btn"
          @click="handleBackToDashboard"
        >
          &larr; 返回
        </button>
        <h1 class="page-title">法律案件分析</h1>
        <p class="page-subtitle">输入案件文本，获取 AI 辅助的法律分析结果</p>
      </div>

      <div class="analysis-layout">
        <div class="analysis-input-section">
          <div class="input-header">
            <label
              class="input-label"
              for="case-text"
            >案件文本</label>
            <div class="input-stats">
              <span class="stat-item">{{ textCharCount }} 字</span>
              <span class="stat-item">{{ textWordCount }} 词</span>
            </div>
          </div>

          <textarea
            id="case-text"
            v-model="caseText"
            class="case-textarea"
            placeholder="请在此粘贴或输入案件文本内容（至少10个字符）..."
            rows="12"
            @input="handleTextInput"
          ></textarea>

          <div
            v-if="submitError"
            class="submit-error"
          >
            <span class="error-icon">⚠️</span>
            <span>{{ submitError }}</span>
          </div>

          <div class="input-actions">
            <button
              class="btn btn-secondary btn-sm"
              @click="handleClearText"
            >
              清空文本
            </button>
            <button
              class="btn btn-primary"
              :disabled="!hasMinimumText || isSubmitting"
              @click="handleSubmit"
            >
              <template v-if="isSubmitting">
                <span class="btn-spinner"></span>
                分析中...
              </template>
              <template v-else>
                开始分析
              </template>
            </button>
          </div>
        </div>

        <div
          v-if="analysisStore.isLoading || analysisStore.analysisResult || analysisStore.error"
          class="analysis-output-section"
        >
          <AnalysisResult
            :result="analysisStore.analysisResult"
            :is-loading="analysisStore.isLoading"
            :error="analysisStore.error"
            :response-time="responseTime"
            @retry="handleRetry"
          />

          <!-- 三维度可视化矩阵 -->
          <div v-if="analysisStore.analysisResult" class="analysis-extra-section">
            <DimensionMatrix :analysis-result="analysisStore.analysisResult" />
          </div>

          <!-- 规则透明度面板 -->
          <div v-if="analysisStore.analysisResult" class="analysis-extra-section">
            <RuleTransparency :analysis-result="analysisStore.analysisResult" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.analysis-page {
  padding: 2rem 0;
  min-height: calc(100vh - 56px);
}

.page-header {
  margin-bottom: 1.5rem;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  font-family: inherit;
  color: var(--color-primary, #4f46e5);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  margin-bottom: 0.75rem;
}

.back-btn:hover {
  text-decoration: underline;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  margin: 0 0 0.5rem;
}

.page-subtitle {
  font-size: 0.9375rem;
  color: var(--text-secondary, #64748b);
  margin: 0;
}

.analysis-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 1024px) {
  .analysis-layout {
    grid-template-columns: 1fr 1fr;
  }
}

.analysis-input-section {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
}

.input-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.input-label {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
}

.input-stats {
  display: flex;
  gap: 1rem;
}

.stat-item {
  font-size: 0.75rem;
  color: var(--text-tertiary, #94a3b8);
}

.case-textarea {
  width: 100%;
  min-height: 300px;
  padding: 1rem;
  font-size: 0.9375rem;
  font-family: inherit;
  line-height: 1.7;
  color: var(--text-primary, #1e293b);
  background: var(--bg-secondary, #f8fafc);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: var(--border-radius, 8px);
  resize: vertical;
  transition: border-color var(--transition-fast, 150ms ease);
  box-sizing: border-box;
}

.case-textarea:focus {
  outline: none;
  border-color: var(--color-primary, #4f46e5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.case-textarea::placeholder {
  color: var(--text-tertiary, #94a3b8);
}

.submit-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  color: var(--color-danger, #ef4444);
  background: rgba(239, 68, 68, 0.06);
  border-radius: var(--border-radius, 8px);
}

.error-icon {
  flex-shrink: 0;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}

.btn-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.analysis-output-section {
  min-height: 400px;
}

.analysis-extra-section {
  margin-top: 1.5rem;
}
</style>