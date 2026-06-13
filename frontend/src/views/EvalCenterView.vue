<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

// 响应式数据
const isRunning = ref(false)
const evalProgress = ref(0)
const evalStatus = ref('')
const evalError = ref(null)
const latestResult = ref(null)
const activeTab = ref('ablation') // 'ablation' | 'benchmark'

// 计算属性
const canRunEval = computed(() => !isRunning.value)
const hasResult = computed(() => latestResult.value !== null)
const ablationResults = computed(() => latestResult.value?.ablation || [])
const benchmarkResults = computed(() => latestResult.value?.benchmark || [])

// 生命周期
onMounted(async () => {
  await fetchLatestResult()
})

// 方法
async function fetchLatestResult() {
  try {
    const response = await axios.get('/api/eval/latest')
    latestResult.value = response.data
  } catch (error) {
    console.error('获取评测结果失败:', error)
  }
}

async function runEval() {
  if (!canRunEval.value) return

  isRunning.value = true
  evalProgress.value = 0
  evalStatus.value = '准备评测环境...'
  evalError.value = null

  try {
    // 模拟评测进度
    const progressInterval = setInterval(() => {
      if (evalProgress.value < 90) {
        evalProgress.value += 10
        updateStatus(evalProgress.value)
      }
    }, 500)

    const response = await axios.post('/api/eval/run')
    clearInterval(progressInterval)

    evalProgress.value = 100
    evalStatus.value = '评测完成'

    latestResult.value = response.data
  } catch (error) {
    evalError.value = error.response?.data?.detail || error.message || '评测失败，请稍后重试'
    evalStatus.value = '评测失败'
  } finally {
    isRunning.value = false
  }
}

function updateStatus(progress) {
  if (progress < 20) {
    evalStatus.value = '加载测试数据集...'
  } else if (progress < 40) {
    evalStatus.value = '运行消融实验...'
  } else if (progress < 60) {
    evalStatus.value = '执行竞品对标...'
  } else if (progress < 80) {
    evalStatus.value = '计算评估指标...'
  } else {
    evalStatus.value = '生成评测报告...'
  }
}

function exportCSV() {
  if (!hasResult.value) return

  const csvContent = generateCSV()
  downloadFile(csvContent, 'eval_result.csv', 'text/csv')
}

function exportPDF() {
  if (!hasResult.value) return

  // 简化实现：实际项目中可能需要使用 jsPDF 等库
  alert('PDF 导出功能开发中')
}

function generateCSV() {
  const rows = [['类型', '实验名称', '指标', '数值']]

  // 添加消融实验数据
  ablationResults.value.forEach((item) => {
    rows.push(['消融实验', item.name, item.metric, item.value])
  })

  // 添加竞品对标数据
  benchmarkResults.value.forEach((item) => {
    rows.push(['竞品对标', item.model, item.metric, item.value])
  })

  return rows.map((row) => row.join(',')).join('\n')
}

function downloadFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function formatValue(value) {
  if (typeof value === 'number') {
    return value.toFixed(4)
  }
  return value
}
</script>

<template>
  <div class="eval-center-page">
    <div class="eval-header">
      <h1 class="eval-title">评测中心</h1>
      <p class="eval-description">运行系统评测，查看消融实验与竞品对标结果</p>
    </div>

    <!-- 评测运行区 -->
    <div class="eval-control-section">
      <div class="control-card">
        <div class="control-header">
          <h2 class="control-title">运行评测</h2>
          <button
            class="run-button"
            :disabled="!canRunEval"
            @click="runEval"
          >
            <span v-if="isRunning" class="spinner"></span>
            {{ isRunning ? '评测中...' : '运行评测' }}
          </button>
        </div>

        <!-- 进度显示 -->
        <div v-if="isRunning" class="progress-section">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: `${evalProgress}%` }"
            ></div>
          </div>
          <div class="progress-info">
            <span class="progress-status">{{ evalStatus }}</span>
            <span class="progress-percent">{{ evalProgress }}%</span>
          </div>
        </div>

        <!-- 错误提示 -->
        <div v-if="evalError" class="error-message">
          {{ evalError }}
        </div>
      </div>
    </div>

    <!-- 评测结果展示 -->
    <div v-if="hasResult" class="result-section">
      <div class="result-header">
        <h2 class="result-title">最近评测结果</h2>
        <div class="export-buttons">
          <button class="export-button" @click="exportCSV">
            导出 CSV
          </button>
          <button class="export-button" @click="exportPDF">
            导出 PDF
          </button>
        </div>
      </div>

      <!-- 标签切换 -->
      <div class="tab-container">
        <button
          class="tab-button"
          :class="{ active: activeTab === 'ablation' }"
          @click="activeTab = 'ablation'"
        >
          消融实验
        </button>
        <button
          class="tab-button"
          :class="{ active: activeTab === 'benchmark' }"
          @click="activeTab = 'benchmark'"
        >
          竞品对标
        </button>
      </div>

      <!-- 消融实验结果 -->
      <div v-if="activeTab === 'ablation'" class="result-table-container">
        <table class="result-table">
          <thead>
            <tr>
              <th>实验名称</th>
              <th>评估指标</th>
              <th>数值</th>
              <th>变化</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in ablationResults" :key="index">
              <td>{{ item.name }}</td>
              <td>{{ item.metric }}</td>
              <td class="value-cell">{{ formatValue(item.value) }}</td>
              <td :class="item.change >= 0 ? 'positive' : 'negative'">
                {{ item.change >= 0 ? '+' : '' }}{{ formatValue(item.change) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 竞品对标结果 -->
      <div v-if="activeTab === 'benchmark'" class="result-table-container">
        <table class="result-table">
          <thead>
            <tr>
              <th>模型</th>
              <th>评估指标</th>
              <th>数值</th>
              <th>排名</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in benchmarkResults" :key="index">
              <td :class="{ 'highlight-row': item.is_ours }">
                {{ item.model }}
                <span v-if="item.is_ours" class="ours-badge">我们的</span>
              </td>
              <td>{{ item.metric }}</td>
              <td class="value-cell">{{ formatValue(item.value) }}</td>
              <td>
                <span class="rank-badge" :class="`rank-${item.rank}`">
                  #{{ item.rank }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 评测元信息 -->
      <div class="eval-meta">
        <div class="meta-item">
          <span class="meta-label">评测时间：</span>
          <span class="meta-value">{{ latestResult?.timestamp }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">测试集大小：</span>
          <span class="meta-value">{{ latestResult?.test_set_size }} 条</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">评测耗时：</span>
          <span class="meta-value">{{ latestResult?.duration }} 秒</span>
        </div>
      </div>
    </div>

    <!-- 无结果提示 -->
    <div v-else class="no-result-section">
      <div class="no-result-icon">📊</div>
      <p class="no-result-text">暂无评测结果</p>
      <p class="no-result-hint">点击"运行评测"按钮开始执行系统评测</p>
    </div>
  </div>
</template>

<style scoped>
.eval-center-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.eval-header {
  margin-bottom: 2rem;
}

.eval-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
  color: #1a1a1a;
}

.eval-description {
  font-size: 1rem;
  color: #666;
  margin: 0;
}

.eval-control-section {
  margin-bottom: 2rem;
}

.control-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.control-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.control-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.run-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.run-button:hover:not(:disabled) {
  background: #2563eb;
}

.run-button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.progress-section {
  margin-top: 1rem;
}

.progress-bar {
  width: 100%;
  height: 0.5rem;
  background: #e5e7eb;
  border-radius: 0.25rem;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s ease;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.progress-status {
  color: #6b7280;
}

.progress-percent {
  font-weight: 600;
  color: #3b82f6;
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #fef2f2;
  color: #dc2626;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.result-section {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.result-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.export-buttons {
  display: flex;
  gap: 0.5rem;
}

.export-button {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.export-button:hover {
  background: #e5e7eb;
}

.tab-container {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.tab-button {
  padding: 0.75rem 1.5rem;
  background: transparent;
  color: #6b7280;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-button:hover {
  color: #3b82f6;
}

.tab-button.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
}

.result-table-container {
  overflow-x: auto;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
}

.result-table th,
.result-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.result-table th {
  background: #f9fafb;
  font-weight: 600;
  color: #374151;
  font-size: 0.875rem;
}

.result-table tbody tr:hover {
  background: #f9fafb;
}

.value-cell {
  font-family: 'Courier New', monospace;
  font-weight: 600;
}

.positive {
  color: #10b981;
}

.negative {
  color: #ef4444;
}

.highlight-row {
  background: #eff6ff;
  font-weight: 600;
}

.ours-badge {
  margin-left: 0.5rem;
  padding: 0.125rem 0.5rem;
  background: #3b82f6;
  color: #fff;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.rank-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.rank-1 {
  background: #fbbf24;
  color: #fff;
}

.rank-2 {
  background: #9ca3af;
  color: #fff;
}

.rank-3 {
  background: #d97706;
  color: #fff;
}

.eval-meta {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.meta-label {
  color: #6b7280;
}

.meta-value {
  font-weight: 600;
  color: #111827;
}

.no-result-section {
  text-align: center;
  padding: 4rem 2rem;
  background: #f9fafb;
  border-radius: 0.75rem;
}

.no-result-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.no-result-text {
  font-size: 1.25rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 0.5rem;
}

.no-result-hint {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
}

@media (max-width: 768px) {
  .eval-center-page {
    padding: 1rem;
  }

  .control-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .result-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .export-buttons {
    justify-content: stretch;
  }

  .export-button {
    flex: 1;
  }

  .eval-meta {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>
