<script setup>
import { ref, computed, watch, onMounted } from 'vue'

import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()

const cases = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const isLoading = ref(false)
const errorMsg = ref(null)

const searchKeyword = ref('')
const filterStatus = ref('')

const isCreateDialogVisible = ref(false)
const isDeleteConfirmVisible = ref(false)
const deletingCase = ref(null)
const isSubmitting = ref(false)

const createForm = ref({
  name: '',
  fact_text: '',
})

const formErrors = ref({
  name: '',
  fact_text: '',
})

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '待分析' },
  { value: 'analyzing', label: '分析中' },
  { value: 'completed', label: '已完成' },
]

const statusConfig = {
  pending: { label: '待分析', class: 'status-pending' },
  analyzing: { label: '分析中', class: 'status-analyzing' },
  completed: { label: '已完成', class: 'status-completed' },
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const canSubmit = computed(() => (
    createForm.value.name.trim().length > 0 &&
    createForm.value.name.trim().length <= 50 &&
    createForm.value.fact_text.trim().length >= 10 &&
    !isSubmitting.value
  ))

watch([searchKeyword, filterStatus], () => {
  currentPage.value = 1
  fetchCases()
})

async function fetchCases() {
  isLoading.value = true
  errorMsg.value = null

  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (searchKeyword.value.trim()) {
      params.search = searchKeyword.value.trim()
    }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }

    const response = await axios.get('/api/cases', { params })
    cases.value = response.data.cases || response.data.items || []
    total.value = response.data.total || 0
  } catch (err) {
    errorMsg.value = err.message || '获取案件列表失败'
    cases.value = []
    total.value = 0
  } finally {
    isLoading.value = false
  }
}

function handleGoToPage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  currentPage.value = page
  fetchCases()
}

function getPaginationPages() {
  const pages = []
  const tp = totalPages.value

  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (currentPage.value > 3) pages.push('...')
    const start = Math.max(2, currentPage.value - 1)
    const end = Math.min(tp - 1, currentPage.value + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (currentPage.value < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
}

function formatTime(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    const pad = (n) => String(n).padStart(2, '0')
    return (
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
      `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    )
  } catch {
    return dateStr
  }
}

function getStatusInfo(status) {
  return statusConfig[status] || { label: status || '未知', class: 'status-pending' }
}

function openCreateDialog() {
  createForm.value = { name: '', fact_text: '' }
  formErrors.value = { name: '', fact_text: '' }
  isCreateDialogVisible.value = true
}

function closeCreateDialog() {
  isCreateDialogVisible.value = false
}

function validateField(field) {
  const val = createForm.value[field]
  if (field === 'name') {
    if (!val.trim()) formErrors.value.name = '案件名称不能为空'
    else if (val.length > 50) formErrors.value.name = '案件名称不能超过50个字符'
    else formErrors.value.name = ''
  } else if (field === 'fact_text') {
    if (!val.trim()) formErrors.value.fact_text = '事实文本不能为空'
    else if (val.trim().length < 10) formErrors.value.fact_text = '事实文本不能少于10个字符'
    else formErrors.value.fact_text = ''
  }
}

async function submitCreateCase() {
  if (!canSubmit.value) return

  isSubmitting.value = true
  try {
    await axios.post('/api/cases', {
      name: createForm.value.name.trim(),
      fact_text: createForm.value.fact_text.trim(),
    })
    closeCreateDialog()
    fetchCases()
  } catch (err) {
    errorMsg.value = err.message || '创建案件失败'
  } finally {
    isSubmitting.value = false
  }
}

function viewDetail(caseItem) {
  router.push({ path: '/report', query: { case_id: caseItem.id } })
}

function handleConfirmDelete(caseItem) {
  deletingCase.value = caseItem
  isDeleteConfirmVisible.value = true
}

function handleCancelDelete() {
  isDeleteConfirmVisible.value = false
  deletingCase.value = null
}

async function handleExecuteDelete() {
  if (!deletingCase.value) return

  try {
    await axios.delete(`/api/cases/${deletingCase.value.id}`)
    isDeleteConfirmVisible.value = false
    deletingCase.value = null
    if (cases.value.length === 1 && currentPage.value > 1) {
      currentPage.value--
    }
    fetchCases()
  } catch (err) {
    errorMsg.value = err.message || '删除案件失败'
    isDeleteConfirmVisible.value = false
    deletingCase.value = null
  }
}

onMounted(() => {
  fetchCases()
})
</script>

<template>
  <div class="cases-page">
    <header class="cases-header">
      <div class="header-left">
        <h1 class="page-title">
          案件管理
        </h1>
        <p class="page-subtitle">
          管理和查看所有分析案件
        </p>
      </div>
      <button
        class="btn btn-primary"
        @click="openCreateDialog"
      >
        <span class="btn-icon">+</span>
        新建案件
      </button>
    </header>

    <div class="filter-bar card">
      <div class="filter-item">
        <label
          class="filter-label"
          for="search-input"
        >案件名称</label>
        <input
          id="search-input"
          v-model="searchKeyword"
          type="text"
          class="filter-input"
          placeholder="输入案件名称搜索..."
        />
      </div>
      <div class="filter-item">
        <label
          class="filter-label"
          for="status-select"
        >分析状态</label>
        <select
          id="status-select"
          v-model="filterStatus"
          class="filter-select"
        >
          <option
            v-for="opt in statusOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>
    </div>

    <div
      v-if="error"
      class="error-alert"
    >
      <span class="error-icon">!</span>
      <span class="error-text">{{ errorMsg }}</span>
      <button
        class="error-close"
        @click="errorMsg = null"
      >
        ×
      </button>
    </div>

    <div class="table-card card">
      <div
        v-if="isLoading"
        class="table-isLoading"
      >
        <div class="isLoading-spinner" ></div>
        <p>正在加载案件数据...</p>
      </div>

      <div
        v-else-if="cases.length === 0"
        class="table-empty"
      >
        <div class="empty-icon">
          📋
        </div>
        <h3 class="empty-title">
          暂无案件数据
        </h3>
        <p class="empty-desc">
          {{ searchKeyword || filterStatus ? '没有匹配的案件，请调整筛选条件' : '点击上方"新建案件"按钮创建第一个案件' }}
        </p>
      </div>

      <div
        v-else
        class="table-wrapper"
      >
        <table class="data-table">
          <thead>
            <tr>
              <th>案件名称</th>
              <th>创建时间</th>
              <th>分析状态</th>
              <th class="col-actions">
                操作
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in cases"
              :key="item.id"
            >
              <td class="cell-name">
                {{ item.name || '未命名案件' }}
              </td>
              <td class="cell-time">
                {{ formatTime(item.created_at || item.createdAt) }}
              </td>
              <td>
                <span
                  class="status-tag"
                  :class="getStatusInfo(item.status).class"
                >
                  {{ getStatusInfo(item.status).label }}
                </span>
              </td>
              <td class="cell-actions">
                <button
                  class="btn btn-sm btn-action btn-action-view"
                  @click="viewDetail(item)"
                >
                  查看详情
                </button>
                <button
                  class="btn btn-sm btn-action btn-action-delete"
                  @click="handleConfirmDelete(item)"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="totalPages > 1 && cases.length > 0"
        class="pagination"
      >
        <button
          class="page-btn"
          :disabled="currentPage <= 1"
          @click="handleGoToPage(currentPage - 1)"
        >
          ‹
        </button>
        <template
          v-for="p in getPaginationPages()"
          :key="p"
        >
          <span
            v-if="p === '...'"
            class="page-ellipsis"
          >…</span>
          <button
            v-else
            class="page-btn"
            :class="{ active: p === currentPage }"
            @click="handleGoToPage(p)"
          >
            {{ p }}
          </button>
        </template>
        <button
          class="page-btn"
          :disabled="currentPage >= totalPages"
          @click="handleGoToPage(currentPage + 1)"
        >
          ›
        </button>
        <span class="page-info">共 {{ total }} 条</span>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="isCreateDialogVisible"
        class="dialog-overlay"
        @click.self="closeCreateDialog"
      >
        <div class="dialog card">
          <div class="dialog-header">
            <h2 class="dialog-title">
              新建案件
            </h2>
            <button
              class="dialog-close"
              @click="closeCreateDialog"
            >
              ×
            </button>
          </div>

          <div class="dialog-body">
            <div class="form-group">
              <label
                class="form-label"
                for="case-name"
              >案件名称</label>
              <input
                id="case-name"
                v-model="createForm.name"
                type="text"
                class="form-input"
                placeholder="请输入案件名称"
                maxlength="50"
                @input="validateField('name')"
              />
              <div class="form-field-footer">
                <span
                  v-if="formErrors.name"
                  class="form-error"
                >{{ formErrors.name }}</span>
                <span class="form-counter">{{ createForm.name.length }}/50</span>
              </div>
            </div>

            <div class="form-group">
              <label
                class="form-label"
                for="case-fact"
              >事实文本</label>
              <textarea
                id="case-fact"
                v-model="createForm.fact_text"
                class="form-textarea"
                placeholder="请输入案件事实描述（不少于10个字符）"
                rows="6"
                @input="validateField('fact_text')"
              ></textarea>
              <span
                v-if="formErrors.fact_text"
                class="form-error"
              >{{ formErrors.fact_text }}</span>
            </div>
          </div>

          <div class="dialog-footer">
            <button
              class="btn btn-secondary"
              @click="closeCreateDialog"
            >
              取消
            </button>
            <button
              class="btn btn-primary"
              :disabled="!canSubmit"
              @click="submitCreateCase"
            >
              {{ isSubmitting ? '提交中...' : '确认创建' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="isDeleteConfirmVisible"
        class="dialog-overlay"
        @click.self="handleCancelDelete"
      >
        <div class="dialog dialog-sm card">
          <div class="dialog-header">
            <h2 class="dialog-title">
              确认删除
            </h2>
            <button
              class="dialog-close"
              @click="handleCancelDelete"
            >
              ×
            </button>
          </div>
          <div class="dialog-body">
            <p class="confirm-text">
              确定要删除此案件吗？此操作不可撤销。
            </p>
            <p
              v-if="deletingCase"
              class="confirm-target"
            >
              「{{ deletingCase.name }}」
            </p>
          </div>
          <div class="dialog-footer">
            <button
              class="btn btn-secondary"
              @click="handleCancelDelete"
            >
              取消
            </button>
            <button
              class="btn btn-danger"
              @click="handleExecuteDelete"
            >
              确认删除
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.cases-page {
  min-height: 100vh;
  background: var(--bg-secondary);
  padding: 2rem 1rem;
}

.cases-header {
  max-width: 1200px;
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

.filter-bar {
  max-width: 1200px;
  margin: 0 auto 1.5rem;
  display: flex;
  gap: 1.5rem;
  align-items: flex-end;
  flex-wrap: wrap;
  padding: 1.25rem 1.5rem;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  min-width: 220px;
  flex: 1;
}

.filter-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.03em;
}

.filter-input,
.filter-select {
  padding: 0.625rem 0.875rem;
  font-size: 0.9rem;
  font-family: inherit;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: border-color var(--transition-fast);
  outline: none;
}

.filter-input:focus,
.filter-select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.filter-select {
  cursor: pointer;
  appearance: auto;
}

.error-alert {
  max-width: 1200px;
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

.table-card {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
  overflow: hidden;
}

.table-isLoading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  gap: 1rem;
  color: var(--text-secondary);
}

.table-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-desc {
  color: var(--text-secondary);
  font-size: 0.9rem;
  max-width: 320px;
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.data-table thead {
  background: var(--bg-tertiary);
}

.data-table th {
  padding: 0.875rem 1.25rem;
  text-align: left;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-color);
  white-space: nowrap;
}

.data-table td {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
  color: var(--text-primary);
}

.data-table tbody tr {
  transition: background var(--transition-fast);
}

.data-table tbody tr:hover {
  background: var(--bg-secondary);
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.col-actions {
  text-align: center;
  width: 180px;
}

.cell-name {
  font-weight: 500;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-time {
  font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.85rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.cell-actions {
  text-align: center;
  white-space: nowrap;
}

.btn-action {
  margin: 0 0.25rem;
  padding: 0.375rem 0.875rem;
  font-size: 0.825rem;
  border: 1px solid transparent;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-action-view {
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary);
  border-color: rgba(79, 70, 229, 0.2);
}

.btn-action-view:hover {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.btn-action-delete {
  background: rgba(239, 68, 68, 0.08);
  color: var(--color-danger);
  border-color: rgba(239, 68, 68, 0.2);
}

.btn-action-delete:hover {
  background: var(--color-danger);
  color: white;
  border-color: var(--color-danger);
}

.status-tag {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 100px;
  white-space: nowrap;
}

.status-pending {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}

.status-analyzing {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.status-completed {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #86efac;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 1.25rem;
  border-top: 1px solid var(--border-color);
  flex-wrap: wrap;
}

.page-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
  padding: 0 0.625rem;
  font-size: 0.875rem;
  font-weight: 500;
  font-family: inherit;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.page-btn:hover:not(:disabled):not(.active) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.page-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-ellipsis {
  padding: 0 0.25rem;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

.page-info {
  margin-left: 0.75rem;
  font-size: 0.825rem;
  color: var(--text-tertiary);
  white-space: nowrap;
}

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

.form-group {
  margin-bottom: 1.25rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.form-input {
  width: 100%;
  padding: 0.625rem 0.875rem;
  font-size: 0.9rem;
  font-family: inherit;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: border-color var(--transition-fast);
  outline: none;
}

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.form-textarea {
  width: 100%;
  padding: 0.625rem 0.875rem;
  font-size: 0.9rem;
  font-family: inherit;
  line-height: 1.6;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-primary);
  resize: vertical;
  transition: border-color var(--transition-fast);
  outline: none;
}

.form-textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.form-field-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.375rem;
}

.form-error {
  font-size: 0.8rem;
  color: var(--color-danger);
}

.form-counter {
  font-size: 0.8rem;
  color: var(--text-tertiary);
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

@media (max-width: 768px) {
  .cases-page {
    padding: 1rem 0.75rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .filter-bar {
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
  }

  .filter-item {
    min-width: 100%;
  }

  .data-table th,
  .data-table td {
    padding: 0.75rem 0.875rem;
    font-size: 0.825rem;
  }

  .cell-name {
    max-width: 160px;
  }

  .col-actions {
    width: 140px;
  }

  .btn-action {
    padding: 0.25rem 0.625rem;
    font-size: 0.75rem;
  }

  .pagination {
    gap: 0.25rem;
    padding: 1rem;
  }

  .page-btn {
    min-width: 32px;
    height: 32px;
    font-size: 0.8rem;
  }

  .dialog {
    max-width: 100%;
    margin: 0.5rem;
  }
}
</style>
