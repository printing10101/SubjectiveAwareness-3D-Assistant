<script setup>
// 1. 导入语句
import { ref, computed, onMounted } from 'vue'

import axios from 'axios'
import { useRouter } from 'vue-router'

import { demoCases } from '../data/demoCases.js'
import { useAnalysisStore } from '../stores/analysisStore.js'

// 4. 组合式函数
const router = useRouter()
const store = useAnalysisStore()

// 5. 响应式数据
const caseText = ref(store.currentCaseText || '')
const textareaRef = ref(null)
const analysisLoading = ref([false, false, false])
const dimensions = ['交易异常性', '沟通内容', '嫌疑人行为']
const showAnalysisDetails = ref(false)
const cachedDemoIds = ref(new Set())

// 6. 计算属性
const canAnalyze = computed(() => caseText.value.trim().length > 0 && !store.isLoading)

const cacheStatusClass = computed(() => {
  if (store.cacheHit === true) return 'cache-hit'
  if (store.cacheHit === false) return 'cache-miss'
  return 'cache-unknown'
})

const cacheStatusIcon = computed(() => {
  if (store.cacheHit === true) return '🟢'
  if (store.cacheHit === false) return '🔴'
  return '🟡'
})

const cacheStatusLabel = computed(() => {
  if (store.cacheHit === true) return '缓存命中（零Token消耗）'
  if (store.cacheHit === false) return '首次分析'
  return '分析中...'
})

// 7. 方法
function handleAutoResize() {
  const textarea = textareaRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 400)}px`
  }
}

function useDemoCase(caseItem) {
  caseText.value = caseItem.text
  store.setCaseText(caseItem.text)
  handleAutoResize()
}

async function checkCacheStatus() {
  try {
    const response = await axios.get('/api/cache/stats')
    const stats = response.data?.cache
    if (!stats?.total_entries) return

    for (const demo of demoCases) {
      try {
        const resp = await axios.post('/api/analyze', { case_text: demo.text })
        if (resp.data?.meta?.cache_hit) {
          cachedDemoIds.value.add(demo.id)
        }
      } catch {
        // 忽略检查失败
      }
    }
  } catch {
    // 忽略错误
  }
}

async function handleStartAnalysis() {
  if (!canAnalyze.value) return

  const startTime = Date.now()
  const cacheKey = store.generateCacheKey(caseText.value)
  const cached = store.getCachedResult(cacheKey)

  if (cached) {
    store.setCacheHit(true)
    store.setResponseTime(0)
    store.setTokensEstimate({
      input: 0,
      output: 0,
      total: 0,
    })
    store.setAnalysisResult(cached)
    store.setCaseText(caseText.value)
    router.push('/report')
    return
  }

  store.setLoading(true)
  store.setError(null)

  try {
    const response = await axios.post('/api/analyze', {
      case_text: caseText.value,
    })

    const elapsed = Date.now() - startTime
    const meta = response.data?.meta

    if (meta) {
      store.setCacheHit(meta.cache_hit)
      store.setResponseTime(meta.response_time_ms || elapsed)
      if (meta.tokens_estimate) {
        const est = meta.tokens_estimate
        store.setTokensEstimate({
          input: est.input || 0,
          output: est.output || 0,
          total: (est.input || 0) + (est.output || 0),
        })
      }
    }

    store.setCachedResult(cacheKey, response.data)
    store.setAnalysisResult(response.data)
    store.setCaseText(caseText.value)

    router.push('/report')
  } catch (error) {
    store.setError(error?.message || '分析失败，请稍后重试')
  } finally {
    store.setLoading(false)
    analysisLoading.value = [false, false, false]
  }
}

// 8. 生命周期钩子
onMounted(() => {
  checkCacheStatus()
})
</script>

<template>
  <div class="main-page">
    <header class="main-header">
      <h1 class="main-title">
        主观明知分析系统
      </h1>
      <p class="main-subtitle">
        输入案件事实，AI 将自动进行多维度分析
      </p>
    </header>

    <div class="main-content">
      <!-- 错误提示 -->
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

      <div class="main-grid">
        <!-- 左侧：输入区域 -->
        <div class="input-section">
          <!-- 案件事实输入 -->
          <div class="input-card card">
            <label
              class="input-label"
              for="case-text"
            >案件事实输入</label>
            <textarea
              id="case-text"
              ref="textareaRef"
              v-model="caseText"
              class="case-textarea"
              placeholder="请在此处输入案件事实描述...&#10;&#10;包括：交易过程、聊天内容、嫌疑人行为等关键信息"
              rows="12"
              @input="handleAutoResize"
            ></textarea>

            <div class="char-count">
              {{ caseText.length }} 字符
            </div>
          </div>

          <!-- Demo 案例按钮 -->
          <div class="demo-section card">
            <h3 class="demo-title">
              快速体验 Demo 案例
            </h3>
            <div class="demo-buttons">
              <div
                v-for="demo in demoCases"
                :key="demo.id"
                class="demo-item-wrapper"
              >
                <button
                  class="demo-btn"
                  :class="`demo-btn--${demo.category}`"
                  @click="useDemoCase(demo)"
                >
                  <span class="demo-btn-icon">{{
                    demo.category === '明显明知' ? '🔴' : demo.category === '边缘情况' ? '🟡' : '🔵'
                  }}</span>
                  <span class="demo-btn-name">{{ demo.name }}</span>
                </button>
                <span
                  v-if="cachedDemoIds.has(demo.id)"
                  class="cached-badge"
                >已缓存</span>
              </div>
            </div>
          </div>

          <!-- 开始分析按钮 -->
          <button
            class="analyze-btn btn-primary btn-lg"
            :disabled="!canAnalyze"
            @click="handleStartAnalysis"
          >
            <span
              v-if="store.isLoading"
              class="analyze-btn-loading"
            >
              <span class="loading-dots">
                <span
                  class="dot"
                  :class="{ active: analysisLoading[0] }"
                ></span>
                <span
                  class="dot"
                  :class="{ active: analysisLoading[1] }"
                ></span>
                <span
                  class="dot"
                  :class="{ active: analysisLoading[2] }"
                ></span>
              </span>
              分析中...
            </span>
            <span v-else>开始分析</span>
          </button>
        </div>

        <!-- 右侧：提示信息区域 -->
        <div class="result-section">
          <div
            v-if="!store.isLoading"
            class="placeholder-card card"
          >
            <div class="placeholder-icon">
              📋
            </div>
            <h3 class="placeholder-title">
              分析报告将在此处展示
            </h3>
            <p class="placeholder-desc">
              请先输入案例并点击"开始分析"
            </p>

            <div class="placeholder-steps">
              <div class="step-item">
                <span class="step-number">1</span>
                <span class="step-text">输入案件事实或使用 Demo 案例</span>
              </div>
              <div class="step-item">
                <span class="step-number">2</span>
                <span class="step-text">点击"开始分析"按钮</span>
              </div>
              <div class="step-item">
                <span class="step-number">3</span>
                <span class="step-text">查看 AI 生成的分析报告</span>
              </div>
            </div>
          </div>

          <!-- 加载动画 -->
          <div
            v-else
            class="loading-card card"
          >
            <div class="loading-header">
              <div class="loading-spinner" ></div>
              <h3 class="loading-title">
                AI 正在分析中...
              </h3>
            </div>

            <div class="dimension-progress">
              <div
                v-for="(dim, index) in dimensions"
                :key="dim"
                class="dimension-item"
                :class="{ active: analysisLoading[index] }"
              >
                <span class="dimension-dot" ></span>
                <span class="dimension-name">{{ dim }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分析详情折叠区域 -->
    <div
      v-if="store.cacheHit !== null"
      class="analysis-details-section"
    >
      <button
        class="details-toggle"
        @click="showAnalysisDetails = !showAnalysisDetails"
      >
        <span class="toggle-icon">{{ showAnalysisDetails ? '▼' : '▶' }}</span>
        <span>分析详情</span>
      </button>

      <div
        v-if="showAnalysisDetails"
        class="details-content card"
      >
        <div class="details-grid">
          <!-- 缓存状态 -->
          <div class="detail-item">
            <div class="detail-label">
              缓存状态
            </div>
            <div
              class="detail-value"
              :class="cacheStatusClass"
            >
              <span class="cache-status-icon">{{ cacheStatusIcon }}</span>
              {{ cacheStatusLabel }}
            </div>
          </div>

          <!-- 响应时间 -->
          <div class="detail-item">
            <div class="detail-label">
              响应时间
            </div>
            <div class="detail-value">
              {{ store.responseTime || '—' }}毫秒
            </div>
          </div>

          <!-- Token估算 -->
          <div
            v-if="store.tokensEstimate"
            class="detail-item"
          >
            <div class="detail-label">
              Token估算
            </div>
            <div class="detail-value token-detail">
              输入{{ store.tokensEstimate.input }} + 输出{{ store.tokensEstimate.output }} = 总计{{ store.tokensEstimate.total }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.main-page {
  min-height: 100vh;
  background: var(--bg-secondary);
  padding: 2rem 1rem;
}

.main-header {
  text-align: center;
  margin-bottom: 2rem;
}

.main-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.main-subtitle {
  color: var(--text-secondary);
  font-size: 1.125rem;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
}

/* 错误提示 */
.error-alert {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--border-radius);
  margin-bottom: 1.5rem;
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
}

.error-text {
  flex: 1;
  color: #991b1b;
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
  0%,
  100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-5px);
  }
  75% {
    transform: translateX(5px);
  }
}

/* 主网格布局 */
.main-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 1024px) {
  .main-grid {
    grid-template-columns: 3fr 2fr;
    gap: 2rem;
  }
}

/* 左侧输入区域 */
.input-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.input-card {
  padding: 1.5rem;
}

.input-label {
  display: block;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}

.case-textarea {
  width: 100%;
  min-height: 200px;
  max-height: 400px;
  padding: 1rem;
  font-size: 1rem;
  line-height: 1.6;
  font-family: inherit;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  resize: vertical;
  transition: border-color var(--transition-fast);
  overflow-y: auto;
}

.case-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.case-textarea::placeholder {
  color: var(--text-tertiary);
}

.char-count {
  text-align: right;
  font-size: 0.8rem;
  color: var(--text-tertiary);
  margin-top: 0.5rem;
}

/* Demo 案例区域 */
.demo-section {
  padding: 1.5rem;
}

.demo-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1rem;
}

.demo-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

@media (min-width: 640px) {
  .demo-buttons {
    flex-direction: row;
  }
}

.demo-item-wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
  flex: 1;
}

.cached-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  background: #dcfce7;
  color: #166534;
  font-size: 0.7rem;
  font-weight: 600;
  border-radius: 4px;
  border: 1px solid #86efac;
}

.demo-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.25rem;
  flex: 1;
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
}

.demo-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.demo-btn--明显明知:hover {
  border-color: #4ade80;
  background: #dcfce7;
}

.demo-btn--边缘情况:hover {
  border-color: #fbbf24;
  background: #fef3c7;
}

.demo-btn--确实不明知:hover {
  border-color: #60a5fa;
  background: #dbeafe;
}

.demo-btn-icon {
  font-size: 1.25rem;
}

.demo-btn-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
}

/* 开始分析按钮 */
.analyze-btn {
  width: 100%;
  padding: 1.25rem 2rem;
  font-size: 1.25rem;
  font-weight: 600;
  border: none;
  border-radius: var(--border-radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: white;
  box-shadow: var(--shadow-lg);
}

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 14px 20px -3px rgba(79, 70, 229, 0.3);
}

.analyze-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.analyze-btn-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.loading-dots {
  display: flex;
  gap: 0.5rem;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transition: all var(--transition-normal);
}

.dot.active {
  background: white;
  transform: scale(1.2);
}

/* 右侧结果区域 */
.result-section {
  display: flex;
  flex-direction: column;
}

.placeholder-card,
.loading-card {
  padding: 2rem;
  text-align: center;
  height: 100%;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.placeholder-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.placeholder-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.placeholder-desc {
  color: var(--text-secondary);
  margin-bottom: 2rem;
}

.placeholder-steps {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  text-align: left;
  width: 100%;
  max-width: 280px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--color-primary);
  color: white;
  border-radius: 50%;
  font-size: 0.875rem;
  font-weight: 600;
  flex-shrink: 0;
}

.step-text {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* 加载状态卡片 */
.loading-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.loading-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.dimension-progress {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
}

.dimension-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
  transition: all var(--transition-normal);
}

.dimension-item.active {
  background: var(--color-primary);
  color: white;
}

.dimension-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--border-color);
  transition: all var(--transition-normal);
}

.dimension-item.active .dimension-dot {
  background: white;
  animation: pulse 1s infinite;
}

.dimension-name {
  font-weight: 500;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 分析详情区域 */
.analysis-details-section {
  max-width: 1200px;
  margin: 1.5rem auto 0;
}

.details-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  padding: 0.5rem 0;
  transition: color var(--transition-fast);
}

.details-toggle:hover {
  color: var(--color-primary);
}

.toggle-icon {
  font-size: 0.75rem;
  transition: transform var(--transition-fast);
}

.details-content {
  padding: 1.25rem 1.5rem;
  margin-top: 0.5rem;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.25rem;
}

.detail-item {
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
}

.detail-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.detail-value {
  font-size: 0.95rem;
  color: var(--text-primary);
  font-weight: 500;
}

/* 缓存状态颜色 */
.cache-hit {
  color: #166534;
}

.cache-miss {
  color: #92400e;
}

.cache-unknown {
  color: var(--text-secondary);
}

.cache-status-icon {
  margin-right: 0.25rem;
}

.token-detail {
  font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.85rem;
  white-space: nowrap;
}
</style>
