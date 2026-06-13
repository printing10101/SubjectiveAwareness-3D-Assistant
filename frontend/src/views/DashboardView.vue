<script setup>
import { ref, onMounted } from 'vue'

import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()

const stats = ref({
  totalCases: 0,
  pendingCases: 0,
  completedCases: 0,
  recentAnalyses: 0,
})

const recentCases = ref([])
const isLoading = ref(true)
const errorMsg = ref(null)

async function fetchDashboardData() {
  isLoading.value = true
  errorMsg.value = null

  try {
    const [statsRes, casesRes] = await Promise.all([
      axios.get('/api/dashboard/stats'),
      axios.get('/api/cases', { params: { page_size: 5, sort_by: 'created_at', sort_order: 'desc' } }),
    ])

    if (statsRes.data) {
      stats.value = {
        totalCases: statsRes.data.total_cases || 0,
        pendingCases: statsRes.data.pending_cases || 0,
        completedCases: statsRes.data.completed_cases || 0,
        recentAnalyses: statsRes.data.recent_analyses || 0,
      }
    }

    recentCases.value = casesRes.data?.cases || casesRes.data?.items || []
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || err.message || '加载仪表盘数据失败'
  } finally {
    isLoading.value = false
  }
}

function handleNavigateToCases() {
  router.push('/cases')
}

function handleNavigateToAnalysis() {
  router.push('/generate')
}

function handleViewCase(caseData) {
  router.push(`/cases/${caseData.id}`)
}

onMounted(() => {
  fetchDashboardData()
})
</script>

<template>
  <div class="dashboard-page">
    <div class="container">
      <div class="page-header">
        <h1 class="page-title">仪表盘</h1>
      </div>

      <div
        v-if="isLoading"
        class="dashboard-loading"
      >
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>

      <div
        v-else-if="errorMsg"
        class="dashboard-error"
      >
        <p>{{ errorMsg }}</p>
        <button
          class="btn btn-primary"
          @click="fetchDashboardData"
        >
          重试
        </button>
      </div>

      <template v-else>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">{{ stats.totalCases }}</div>
            <div class="stat-label">案件总数</div>
          </div>
          <div class="stat-card stat-pending">
            <div class="stat-value">{{ stats.pendingCases }}</div>
            <div class="stat-label">待分析</div>
          </div>
          <div class="stat-card stat-completed">
            <div class="stat-value">{{ stats.completedCases }}</div>
            <div class="stat-label">已完成</div>
          </div>
          <div class="stat-card stat-recent">
            <div class="stat-value">{{ stats.recentAnalyses }}</div>
            <div class="stat-label">近期分析</div>
          </div>
        </div>

        <div class="dashboard-actions">
          <button
            class="btn btn-primary"
            @click="handleNavigateToAnalysis"
          >
            新建分析
          </button>
          <button
            class="btn btn-secondary"
            @click="handleNavigateToCases"
          >
            查看所有案件
          </button>
        </div>

        <div class="recent-section">
          <h2 class="section-title">近期案件</h2>
          <div
            v-if="recentCases.length === 0"
            class="empty-state"
          >
            <p>暂无案件数据</p>
          </div>
          <div
            v-else
            class="recent-list"
          >
            <div
              v-for="caseItem in recentCases"
              :key="caseItem.id"
              class="recent-item"
              @click="handleViewCase(caseItem)"
            >
              <div class="recent-item-info">
                <h3 class="recent-item-name">{{ caseItem.name || '未命名案件' }}</h3>
                <p class="recent-item-date">
                  {{ new Date(caseItem.created_at).toLocaleDateString('zh-CN') }}
                </p>
              </div>
              <span
                class="recent-item-status"
                :class="'status-' + (caseItem.status || 'pending')"
              >
                {{ caseItem.status === 'completed' ? '已完成' : caseItem.status === 'analyzing' ? '分析中' : '待分析' }}
              </span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.dashboard-page {
  padding: 2rem 0;
  min-height: calc(100vh - 56px);
}

.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  margin: 0;
}

.dashboard-loading {
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

.dashboard-error {
  text-align: center;
  padding: 3rem;
  color: var(--color-danger, #ef4444);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  padding: 1.5rem;
  text-align: center;
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-secondary, #64748b);
}

.stat-pending .stat-value {
  color: var(--color-warning, #eab308);
}

.stat-completed .stat-value {
  color: var(--color-success, #22c55e);
}

.stat-recent .stat-value {
  color: var(--color-info, #3b82f6);
}

.dashboard-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.recent-section {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0 0 1rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-tertiary, #94a3b8);
}

.recent-list {
  display: flex;
  flex-direction: column;
}

.recent-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 0;
  border-bottom: 1px solid var(--border-color, #e2e8f0);
  cursor: pointer;
  transition: background var(--transition-fast, 150ms ease);
}

.recent-item:last-child {
  border-bottom: none;
}

.recent-item:hover {
  background: var(--bg-secondary, #f8fafc);
}

.recent-item-info {
  flex: 1;
  min-width: 0;
}

.recent-item-name {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary, #1e293b);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-item-date {
  font-size: 0.75rem;
  color: var(--text-tertiary, #94a3b8);
  margin: 0.25rem 0 0;
}

.recent-item-status {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  flex-shrink: 0;
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

@media (max-width: 767px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .dashboard-actions {
    flex-direction: column;
  }
}
</style>