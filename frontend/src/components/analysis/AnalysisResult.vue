<script setup>
defineOptions({ name: 'AnalysisResult' })

const props = defineProps({
  result: {
    type: Object,
    default: null,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: null,
  },
  responseTime: {
    type: Number,
    default: null,
  },
})

const emit = defineEmits(['retry', 'export', 'save'])

function handleRetry() {
  emit('retry')
}

function handleExport() {
  emit('export', props.result)
}

function handleSave() {
  emit('save', props.result)
}
</script>

<template>
  <div class="analysis-result">
    <!-- 加载状态 -->
    <div
      v-if="isLoading"
      class="analysis-loading"
    >
      <div class="loading-spinner"></div>
      <p class="loading-text">AI 正在分析案例，请稍候...</p>
    </div>

    <!-- 错误状态 -->
    <div
      v-else-if="error"
      class="analysis-error"
    >
      <div class="error-icon">⚠️</div>
      <p class="error-message">{{ error }}</p>
      <button
        class="retry-btn"
        @click="handleRetry"
      >
        重新分析
      </button>
    </div>

    <!-- 分析结果 -->
    <template v-else-if="result">
      <div class="result-header">
        <h3 class="result-title">分析结果</h3>
        <div class="result-meta">
          <span
            v-if="responseTime"
            class="result-time"
          >
            耗时 {{ (responseTime / 1000).toFixed(1) }}s
          </span>
          <div class="result-actions">
            <button
              class="result-btn"
              @click="handleExport"
            >
              导出
            </button>
            <button
              class="result-btn result-btn-primary"
              @click="handleSave"
            >
              保存
            </button>
          </div>
        </div>
      </div>

      <div class="result-content">
        <div
          v-if="result.legal_analysis"
          class="result-section"
        >
          <h4 class="section-title">法律分析</h4>
          <div class="section-body">
            <p
              v-if="result.legal_analysis.subjective_knowing"
              class="analysis-item"
            >
              <strong>主观明知判断：</strong>
              {{ result.legal_analysis.subjective_knowing }}
            </p>
            <p
              v-if="result.legal_analysis.legal_basis"
              class="analysis-item"
            >
              <strong>法律依据：</strong>
              {{ result.legal_analysis.legal_basis }}
            </p>
            <p
              v-if="result.legal_analysis.risk_level"
              class="analysis-item"
            >
              <strong>风险等级：</strong>
              <span
                class="risk-badge"
                :class="'risk-' + result.legal_analysis.risk_level"
              >
                {{ result.legal_analysis.risk_level }}
              </span>
            </p>
          </div>
        </div>

        <div
          v-if="result.key_factors && result.key_factors.length"
          class="result-section"
        >
          <h4 class="section-title">关键因素</h4>
          <ul class="factor-list">
            <li
              v-for="(factor, index) in result.key_factors"
              :key="index"
              class="factor-item"
            >
              {{ factor }}
            </li>
          </ul>
        </div>

        <div
          v-if="result.recommendation"
          class="result-section"
        >
          <h4 class="section-title">建议</h4>
          <p class="section-body">{{ result.recommendation }}</p>
        </div>

        <div
          v-if="result.raw_text"
          class="result-section"
        >
          <h4 class="section-title">详细分析</h4>
          <div class="raw-text">{{ result.raw_text }}</div>
        </div>
      </div>
    </template>

    <!-- 空状态 -->
    <div
      v-else
      class="analysis-empty"
    >
      <div class="empty-icon">📋</div>
      <p class="empty-text">暂无分析结果</p>
      <p class="empty-hint">请先提交案例文本进行分析</p>
    </div>
  </div>
</template>

<style scoped>
.analysis-result {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
  overflow: hidden;
}

/* Loading */
.analysis-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1.25rem;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--bg-tertiary, #f1f5f9);
  border-top-color: var(--color-primary, #4f46e5);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 1rem;
  color: var(--text-secondary, #64748b);
  margin: 0;
}

/* Error */
.analysis-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 1rem;
  text-align: center;
}

.error-icon {
  font-size: 2.5rem;
}

.error-message {
  font-size: 0.9375rem;
  color: var(--color-danger, #ef4444);
  margin: 0;
}

.retry-btn {
  font-size: 0.875rem;
  font-weight: 500;
  font-family: inherit;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: var(--border-radius, 8px);
  cursor: pointer;
  color: #fff;
  background: var(--color-primary, #4f46e5);
  transition: background var(--transition-fast, 150ms ease);
}

.retry-btn:hover {
  background: var(--color-primary-hover, #4338ca);
}

/* Result Header */
.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border-color, #e2e8f0);
  flex-wrap: wrap;
  gap: 0.75rem;
}

.result-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.result-time {
  font-size: 0.8125rem;
  color: var(--text-tertiary, #94a3b8);
}

.result-actions {
  display: flex;
  gap: 0.5rem;
}

.result-btn {
  font-size: 0.8125rem;
  font-weight: 500;
  font-family: inherit;
  padding: 0.375rem 0.875rem;
  border: none;
  border-radius: var(--border-radius, 8px);
  cursor: pointer;
  transition: all var(--transition-fast, 150ms ease);
  color: var(--text-secondary, #64748b);
  background: var(--bg-tertiary, #f1f5f9);
}

.result-btn:hover {
  background: var(--border-color, #e2e8f0);
}

.result-btn-primary {
  color: #fff;
  background: var(--color-primary, #4f46e5);
}

.result-btn-primary:hover {
  background: var(--color-primary-hover, #4338ca);
}

/* Content */
.result-content {
  padding: 1.5rem;
}

.result-section {
  margin-bottom: 1.5rem;
}

.result-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0 0 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-color, #e2e8f0);
}

.section-body {
  font-size: 0.9rem;
  color: var(--text-secondary, #64748b);
  line-height: 1.7;
  margin: 0;
}

.analysis-item {
  margin-bottom: 0.5rem;
}

.analysis-item:last-child {
  margin-bottom: 0;
}

.risk-badge {
  display: inline-block;
  font-size: 0.8125rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
}

.risk-low {
  color: #166534;
  background: rgba(34, 197, 94, 0.12);
}

.risk-medium {
  color: #92400e;
  background: rgba(234, 179, 8, 0.12);
}

.risk-high {
  color: #991b1b;
  background: rgba(239, 68, 68, 0.12);
}

/* Factors */
.factor-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.factor-item {
  font-size: 0.9rem;
  color: var(--text-secondary, #64748b);
  padding: 0.5rem 0;
  padding-left: 1.25rem;
  position: relative;
}

.factor-item::before {
  content: '•';
  position: absolute;
  left: 0.25rem;
  color: var(--color-primary, #4f46e5);
  font-weight: bold;
}

/* Raw Text */
.raw-text {
  font-size: 0.875rem;
  color: var(--text-secondary, #64748b);
  line-height: 1.8;
  white-space: pre-wrap;
}

/* Empty */
.analysis-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 0.75rem;
  text-align: center;
}

.empty-icon {
  font-size: 2.5rem;
}

.empty-text {
  font-size: 1rem;
  color: var(--text-secondary, #64748b);
  margin: 0;
}

.empty-hint {
  font-size: 0.875rem;
  color: var(--text-tertiary, #94a3b8);
  margin: 0;
}
</style>