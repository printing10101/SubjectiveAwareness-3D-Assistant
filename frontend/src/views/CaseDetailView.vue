<script setup>
import { ref, computed, onMounted } from 'vue'

import axios from 'axios'
import { useRoute, useRouter } from 'vue-router'

import { useCaseStore } from '../stores/case.js'
import { formatDate, formatStatus } from '../utils/formatters.js'

const route = useRoute()
const router = useRouter()
const caseStore = useCaseStore()

const caseId = computed(() => route.params.id)
const caseData = ref(null)
const isLoading = ref(true)
const errorMsg = ref(null)
const isDeleting = ref(false)
const isDeleteConfirmVisible = ref(false)

async function fetchCaseDetail() {
  isLoading.value = true
  errorMsg.value = null

  try {
    const response = await axios.get(`/api/cases/${caseId.value}`)
    caseData.value = response.data
    caseStore.setCurrentCase(response.data)
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || err.message || '加载案件详情失败'
  } finally {
    isLoading.value = false
  }
}

function handleBack() {
  router.push('/cases')
}

function handleAnalyze() {
  if (caseData.value) {
    router.push({
      name: 'generate',
      query: { caseId: caseData.value.id },
    })
  }
}

function handleEdit() {
  router.push(`/cases/${caseId.value}/edit`)
}

function handleDeleteConfirm() {
  isDeleteConfirmVisible.value = true
}

function handleDeleteCancel() {
  isDeleteConfirmVisible.value = false
}

async function handleDelete() {
  isDeleting.value = true

  try {
    await axios.delete(`/api/cases/${caseId.value}`)
    caseStore.removeCase(caseId.value)
    router.push('/cases')
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || err.message || '删除案件失败'
    isDeleteConfirmVisible.value = false
  } finally {
    isDeleting.value = false
  }
}

function handleViewAnalysis() {
  if (caseData.value?.analysis_id) {
    router.push(`/analysis/${caseData.value.analysis_id}`)
  }
}

onMounted(() => {
  fetchCaseDetail()
})
</script>

<template>
  <div class="case-detail-page">
    <div class="container">
      <button
        class="back-btn"
        @click="handleBack"
      >
        &larr; 返回案件列表
      </button>

      <div
        v-if="isLoading"
        class="detail-loading"
      >
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>

      <div
        v-else-if="errorMsg"
        class="detail-error"
      >
        <p>{{ errorMsg }}</p>
        <button
          class="btn btn-primary"
          @click="fetchCaseDetail"
        >
          重试
        </button>
      </div>

      <template v-else-if="caseData">
        <div class="detail-header">
          <div class="detail-title-row">
            <h1 class="detail-title">{{ caseData.name || '未命名案件' }}</h1>
            <span
              class="detail-status"
              :class="'status-' + (caseData.status || 'pending')"
            >
              {{ formatStatus(caseData.status) }}
            </span>
          </div>
          <p
            v-if="caseData.created_at"
            class="detail-meta"
          >
            创建时间：{{ formatDate(caseData.created_at, { format: 'datetime' }) }}
          </p>
        </div>

        <div class="detail-actions">
          <button
            class="btn btn-primary"
            @click="handleAnalyze"
          >
            执行分析
          </button>
          <button
            v-if="caseData.analysis_id"
            class="btn btn-secondary"
            @click="handleViewAnalysis"
          >
            查看分析结果
          </button>
          <button
            class="btn btn-secondary"
            @click="handleEdit"
          >
            编辑
          </button>
          <button
            class="btn btn-danger"
            @click="handleDeleteConfirm"
          >
            删除
          </button>
        </div>

        <div class="detail-content">
          <div class="detail-section">
            <h2 class="section-heading">案件事实</h2>
            <div class="fact-text">
              {{ caseData.fact_text || caseData.description || '暂无案件描述' }}
            </div>
          </div>

          <div
            v-if="caseData.analysis_result"
            class="detail-section"
          >
            <h2 class="section-heading">分析结果摘要</h2>
            <div class="analysis-summary">
              <div
                v-if="caseData.analysis_result.legal_analysis"
                class="summary-block"
              >
                <h3>法律分析</h3>
                <p>{{ caseData.analysis_result.legal_analysis }}</p>
              </div>
              <div
                v-if="caseData.analysis_result.recommendation"
                class="summary-block"
              >
                <h3>建议</h3>
                <p>{{ caseData.analysis_result.recommendation }}</p>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 删除确认弹窗 -->
      <div
        v-if="isDeleteConfirmVisible"
        class="modal-overlay"
        @click.self="handleDeleteCancel"
      >
        <div class="modal-content">
          <h3 class="modal-title">确认删除</h3>
          <p class="modal-body">
            确定要删除案件「{{ caseData?.name || '未命名案件' }}」吗？此操作不可撤销。
          </p>
          <div class="modal-actions">
            <button
              class="btn btn-secondary"
              :disabled="isDeleting"
              @click="handleDeleteCancel"
            >
              取消
            </button>
            <button
              class="btn btn-danger"
              :disabled="isDeleting"
              @click="handleDelete"
            >
              {{ isDeleting ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.case-detail-page {
  padding: 2rem 0;
  min-height: calc(100vh - 56px);
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
  margin-bottom: 1.5rem;
}

.back-btn:hover {
  text-decoration: underline;
}

.detail-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4rem;
  gap: 1rem;
  color: var(--text-secondary, #64748b);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--bg-tertiary, #f1f5f9);
  border-top-color: var(--color-primary, #4f46e5);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.detail-error {
  text-align: center;
  padding: 3rem;
  color: var(--color-danger, #ef4444);
}

.detail-header {
  margin-bottom: 1.5rem;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.detail-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  margin: 0;
}

.detail-status {
  font-size: 0.8125rem;
  font-weight: 500;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
}

.status-pending {
  color: #92400e;
  background: rgba(234, 179, 8, 0.12);
}

.status-analyzing {
  color: #1e40af;
  background: rgba(59, 130, 246, 0.12);
}

.status-completed {
  color: #166534;
  background: rgba(34, 197, 94, 0.12);
}

.detail-meta {
  font-size: 0.875rem;
  color: var(--text-tertiary, #94a3b8);
  margin: 0;
}

.detail-actions {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.detail-section {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
}

.section-heading {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0 0 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-color, #e2e8f0);
}

.fact-text {
  font-size: 0.9375rem;
  color: var(--text-secondary, #64748b);
  line-height: 1.8;
  white-space: pre-wrap;
}

.analysis-summary {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.summary-block h3 {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0 0 0.5rem;
}

.summary-block p {
  font-size: 0.9rem;
  color: var(--text-secondary, #64748b);
  line-height: 1.7;
  margin: 0;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 1rem;
}

.modal-content {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  padding: 1.5rem;
  max-width: 400px;
  width: 100%;
  box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0 0 0.75rem;
}

.modal-body {
  font-size: 0.9375rem;
  color: var(--text-secondary, #64748b);
  margin: 0 0 1.25rem;
  line-height: 1.6;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

@media (max-width: 767px) {
  .detail-title {
    font-size: 1.25rem;
  }

  .detail-actions {
    flex-direction: column;
  }
}
</style>