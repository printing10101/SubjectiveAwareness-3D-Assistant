<script setup>
import { ref, computed, watch, onMounted } from 'vue'

import axios from 'axios'

const activeTab = ref('rules')
const currentUser = ref(null)
const isAdmin = computed(() => currentUser.value?.role === 'admin')

const sidebarTabs = [
  { key: 'rules', label: '法律规则', icon: '⚖️', adminOnly: true },
  { key: 'model', label: '模型版本', icon: '🤖', adminOnly: false },
  { key: 'logs', label: '系统日志', icon: '📋', adminOnly: false },
  { key: 'users', label: '用户管理', icon: '👥', adminOnly: true },
]

const visibleTabs = computed(() =>
  sidebarTabs.filter(t => !t.adminOnly || isAdmin.value)
)

const _isLoading = ref(false)
const errorMsg = ref(null)

async function fetchCurrentUser() {
  try {
    const token = localStorage.getItem('access_token')
    if (!token) return
    const res = await axios.get('/api/me')
    currentUser.value = res.data
  } catch {
    currentUser.value = null
  }
}

onMounted(() => {
  fetchCurrentUser()
})

function formatTime(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return dateStr
  }
}

const ruleForm = ref({
  rule_id: '',
  name: '',
  description: '',
  source_law: '',
  article: '',
  conditions: '',
  conclusion: '',
  evidence_types: '',
  weight: 1.0,
})

const ruleFormErrors = ref({})
const isRuleDialogVisible = ref(false)
const editingRule = ref(null)
const isRuleSubmitting = ref(false)

const rules = ref([])
const rulesTotal = ref(0)
const rulesPage = ref(1)
const rulesPageSize = ref(10)
const rulesSearch = ref('')
const isRulesLoading = ref(false)

const rulesTotalPages = computed(() => Math.max(1, Math.ceil(rulesTotal.value / rulesPageSize.value)))

watch(rulesSearch, () => {
  rulesPage.value = 1
  fetchRules()
})

async function fetchRules() {
  isRulesLoading.value = true
  try {
    const params = { page: rulesPage.value, page_size: rulesPageSize.value }
    if (rulesSearch.value.trim()) params.search = rulesSearch.value.trim()
    const res = await axios.get('/api/rules', { params })
    rules.value = res.data.items || []
    rulesTotal.value = res.data.total || 0
  } catch (err) {
    errorMsg.value = err.message || '获取规则列表失败'
    rules.value = []
  } finally {
    isRulesLoading.value = false
  }
}

function handleOpenCreateRule() {
  editingRule.value = null
  ruleForm.value = { rule_id: '', name: '', description: '', source_law: '', article: '', conditions: '', conclusion: '', evidence_types: '', weight: 1.0 }
  ruleFormErrors.value = {}
  isRuleDialogVisible.value = true
}

function handleOpenEditRule(rule) {
  editingRule.value = rule
  ruleForm.value = {
    rule_id: rule.rule_id,
    name: rule.name,
    description: rule.description || '',
    source_law: rule.source_law || '',
    article: rule.article || '',
    conditions: Array.isArray(rule.conditions) ? rule.conditions.join('|') : rule.conditions || '',
    conclusion: rule.conclusion || '',
    evidence_types: Array.isArray(rule.evidence_types) ? rule.evidence_types.join('|') : rule.evidence_types || '',
    weight: rule.weight || 1.0,
  }
  ruleFormErrors.value = {}
  isRuleDialogVisible.value = true
}

function handleCloseRuleDialog() {
  isRuleDialogVisible.value = false
}

function validateRuleForm() {
  const errors = {}
  if (!ruleForm.value.rule_id.trim()) errors.rule_id = '规则ID不能为空'
  if (!ruleForm.value.name.trim()) errors.name = '规则名称不能为空'
  if (ruleForm.value.weight < 0 || ruleForm.value.weight > 1) errors.weight = '权重必须在0-1之间'
  ruleFormErrors.value = errors
  return Object.keys(errors).length === 0
}

async function handleSubmitRule() {
  if (!validateRuleForm()) return
  isRuleSubmitting.value = true
  try {
    if (editingRule.value) {
      const payload = {}
      for (const key of ['name', 'description', 'source_law', 'article', 'conditions', 'conclusion', 'evidence_types']) {
        if (ruleForm.value[key] !== editingRule.value[key]) payload[key] = ruleForm.value[key]
      }
      if (ruleForm.value.weight !== editingRule.value.weight) payload.weight = ruleForm.value.weight
      await axios.put(`/api/rules/${editingRule.value.id}`, payload)
    } else {
      await axios.post('/api/rules', ruleForm.value)
    }
    handleCloseRuleDialog()
    fetchRules()
  } catch (err) {
    errorMsg.value = err.message || '保存规则失败'
  } finally {
    isRuleSubmitting.value = false
  }
}

async function handleDeleteRule(rule) {
  if (!confirm(`确定要删除规则「${rule.name}」吗？`)) return
  try {
    await axios.delete(`/api/rules/${rule.id}`)
    if (rules.value.length === 1 && rulesPage.value > 1) rulesPage.value--
    fetchRules()
  } catch (err) {
    errorMsg.value = err.message || '删除规则失败'
  }
}

function handleGoToRulesPage(page) {
  if (page < 1 || page > rulesTotalPages.value || page === rulesPage.value) return
  rulesPage.value = page
  fetchRules()
}

function getRulesPaginationPages() {
  const pages = []
  const tp = rulesTotalPages.value
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (rulesPage.value > 3) pages.push('...')
    const start = Math.max(2, rulesPage.value - 1)
    const end = Math.min(tp - 1, rulesPage.value + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (rulesPage.value < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
}

const modelInfo = ref(null)
const isModelLoading = ref(false)

async function fetchModelVersion() {
  isModelLoading.value = true
  try {
    const res = await axios.get('/api/model-version')
    modelInfo.value = res.data
  } catch {
    modelInfo.value = null
  } finally {
    isModelLoading.value = false
  }
}

const logs = ref([])
const logsTotal = ref(0)
const logsPage = ref(1)
const logsPageSize = ref(20)
const logLevelFilter = ref('')
const logSearch = ref('')
const isLogsLoading = ref(false)

const logsTotalPages = computed(() => Math.max(1, Math.ceil(logsTotal.value / logsPageSize.value)))

const logLevels = [
  { value: '', label: '全部级别' },
  { value: 'INFO', label: 'INFO' },
  { value: 'WARNING', label: 'WARNING' },
  { value: 'ERROR', label: 'ERROR' },
  { value: 'DEBUG', label: 'DEBUG' },
]

watch([logLevelFilter, logSearch], () => {
  logsPage.value = 1
  fetchLogs()
})

async function fetchLogs() {
  isLogsLoading.value = true
  try {
    const params = { page: logsPage.value, page_size: logsPageSize.value }
    if (logLevelFilter.value) params.log_level = logLevelFilter.value
    if (logSearch.value.trim()) params.search = logSearch.value.trim()
    const res = await axios.get('/api/logs', { params })
    logs.value = res.data.items || []
    logsTotal.value = res.data.total || 0
  } catch {
    logs.value = []
    logsTotal.value = 0
  } finally {
    isLogsLoading.value = false
  }
}

function handleGoToLogsPage(page) {
  if (page < 1 || page > logsTotalPages.value || page === logsPage.value) return
  logsPage.value = page
  fetchLogs()
}

function getLogsPaginationPages() {
  const pages = []
  const tp = logsTotalPages.value
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (logsPage.value > 3) pages.push('...')
    const start = Math.max(2, logsPage.value - 1)
    const end = Math.min(tp - 1, logsPage.value + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (logsPage.value < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
}

function getLogLevelClass(level) {
  const map = {
    ERROR: 'log-error',
    WARNING: 'log-warning',
    INFO: 'log-info',
    DEBUG: 'log-debug',
  }
  return map[level] || 'log-info'
}

const users = ref([])
const usersTotal = ref(0)
const usersPage = ref(1)
const usersPageSize = ref(10)
const isUsersLoading = ref(false)

const usersTotalPages = computed(() => Math.max(1, Math.ceil(usersTotal.value / usersPageSize.value)))

const isUserDialogVisible = ref(false)
const userForm = ref({ username: '', password: '', role: 'user' })
const userFormErrors = ref({})
const isUserSubmitting = ref(false)

const isResetPwdDialogVisible = ref(false)
const resetPwdTarget = ref(null)
const resetPwdForm = ref({ new_password: '' })
const resetPwdErrors = ref({})
const isResetPwdSubmitting = ref(false)

async function fetchUsers() {
  isUsersLoading.value = true
  try {
    const res = await axios.get('/api/users', { params: { page: usersPage.value, page_size: usersPageSize.value } })
    users.value = res.data.items || []
    usersTotal.value = res.data.total || 0
  } catch {
    users.value = []
    usersTotal.value = 0
  } finally {
    isUsersLoading.value = false
  }
}

function handleOpenCreateUser() {
  userForm.value = { username: '', password: '', role: 'user' }
  userFormErrors.value = {}
  isUserDialogVisible.value = true
}

function handleCloseUserDialog() {
  isUserDialogVisible.value = false
}

function validateUserForm() {
  const errors = {}
  if (!userForm.value.username.trim()) errors.username = '用户名不能为空'
  else if (userForm.value.username.trim().length < 2) errors.username = '用户名至少2个字符'
  if (!userForm.value.password) errors.password = '密码不能为空'
  else if (userForm.value.password.length < 6) errors.password = '密码至少6个字符'
  userFormErrors.value = errors
  return Object.keys(errors).length === 0
}

async function handleSubmitUser() {
  if (!validateUserForm()) return
  isUserSubmitting.value = true
  try {
    await axios.post('/api/users', userForm.value)
    handleCloseUserDialog()
    fetchUsers()
  } catch (err) {
    errorMsg.value = err.message || '创建用户失败'
  } finally {
    isUserSubmitting.value = false
  }
}

async function handleToggleUserStatus(user) {
  try {
    await axios.put(`/api/users/${user.id}`, { is_active: !user.is_active })
    fetchUsers()
  } catch (err) {
    errorMsg.value = err.message || '操作失败'
  }
}

function handleOpenResetPwd(user) {
  resetPwdTarget.value = user
  resetPwdForm.value = { new_password: '' }
  resetPwdErrors.value = {}
  isResetPwdDialogVisible.value = true
}

function handleCloseResetPwd() {
  isResetPwdDialogVisible.value = false
  resetPwdTarget.value = null
}

function validateResetPwd() {
  const errors = {}
  if (!resetPwdForm.value.new_password) errors.new_password = '新密码不能为空'
  else if (resetPwdForm.value.new_password.length < 6) errors.new_password = '密码至少6个字符'
  resetPwdErrors.value = errors
  return Object.keys(errors).length === 0
}

async function handleSubmitResetPwd() {
  if (!validateResetPwd()) return
  isResetPwdSubmitting.value = true
  try {
    await axios.post(`/api/users/${resetPwdTarget.value.id}/reset-password`, resetPwdForm.value)
    handleCloseResetPwd()
  } catch (err) {
    errorMsg.value = err.message || '重置密码失败'
  } finally {
    isResetPwdSubmitting.value = false
  }
}

function handleGoToUsersPage(page) {
  if (page < 1 || page > usersTotalPages.value || page === usersPage.value) return
  usersPage.value = page
  fetchUsers()
}

function getUsersPaginationPages() {
  const pages = []
  const tp = usersTotalPages.value
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (usersPage.value > 3) pages.push('...')
    const start = Math.max(2, usersPage.value - 1)
    const end = Math.min(tp - 1, usersPage.value + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (usersPage.value < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
}

watch(activeTab, (tab) => {
  errorMsg.value = null
  if (tab === 'rules') fetchRules()
  else if (tab === 'model') fetchModelVersion()
  else if (tab === 'logs') fetchLogs()
  else if (tab === 'users') fetchUsers()
})

onMounted(() => {
  if (isAdmin.value) {
    fetchRules()
  } else {
    fetchModelVersion()
  }
})
</script>

<template>
  <div class="settings-page">
    <header class="settings-header">
      <div class="header-left">
        <h1 class="page-title">系统管理</h1>
        <p class="page-subtitle">管理系统配置、用户、日志和版本信息</p>
      </div>
    </header>

    <div v-if="!currentUser" class="unauthenticated card">
      <div class="unauth-icon">🔒</div>
      <h3>请先登录</h3>
      <p>您需要登录后才能访问系统管理页面</p>
      <button class="btn btn-primary" @click="$router.push('/')">前往登录</button>
    </div>

    <template v-else>
      <div class="settings-layout">
        <aside class="settings-sidebar">
          <nav class="sidebar-nav">
            <button
              v-for="tab in visibleTabs"
              :key="tab.key"
              class="sidebar-link"
              :class="{ active: activeTab === tab.key }"
              @click="activeTab = tab.key"
            >
              <span class="sidebar-icon">{{ tab.icon }}</span>
              <span class="sidebar-label">{{ tab.label }}</span>
            </button>
          </nav>
        </aside>

        <main class="settings-content">
          <div v-if="error" class="error-alert">
            <span class="error-icon">!</span>
            <span class="error-text">{{ error }}</span>
            <button class="error-close" @click="error = null">×</button>
          </div>

          <div v-if="activeTab === 'rules'" class="tab-content">
            <div class="tab-header">
              <h2 class="tab-title">法律规则配置</h2>
              <button class="btn btn-primary btn-sm" @click="handleOpenCreateRule">+ 新增规则</button>
            </div>

            <div class="filter-bar card">
              <div class="filter-item">
                <label class="filter-label" for="rule-search">搜索规则</label>
                <input
                  id="rule-search"
                  v-model="rulesSearch"
                  type="text"
                  class="filter-input"
                  placeholder="按名称、ID或描述搜索..."/>
              </div>
            </div>

            <div class="table-card card">
              <div v-if="isRulesLoading" class="table-loading">
                <div class="loading-spinner" ></div>
                <p>正在加载规则数据...</p>
              </div>
              <div v-else-if="rules.length === 0" class="table-empty">
                <div class="empty-icon">📜</div>
                <h3 class="empty-title">暂无规则数据</h3>
                <p class="empty-desc">{{ rulesSearch ? '没有匹配的规则，请调整搜索条件' : '点击"新增规则"按钮创建第一条规则' }}</p>
              </div>
              <div v-else class="table-wrapper">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>规则ID</th>
                      <th>名称</th>
                      <th>描述</th>
                      <th>权重</th>
                      <th>创建时间</th>
                      <th class="col-actions">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="rule in rules" :key="rule.id">
                      <td class="cell-rule-id">{{ rule.rule_id }}</td>
                      <td class="cell-name">{{ rule.name }}</td>
                      <td class="cell-desc">{{ rule.description || '—' }}</td>
                      <td>
                        <span class="weight-badge">{{ rule.weight.toFixed(2) }}</span>
                      </td>
                      <td class="cell-time">{{ formatTime(rule.created_at) }}</td>
                      <td class="cell-actions">
                        <button class="btn btn-sm btn-action btn-action-view" @click="handleOpenEditRule(rule)">编辑</button>
                        <button class="btn btn-sm btn-action btn-action-delete" @click="handleDeleteRule(rule)">删除</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-if="rulesTotalPages > 1 && rules.length > 0" class="pagination">
                <button class="page-btn" :disabled="rulesPage <= 1" @click="handleGoToRulesPage(rulesPage - 1)">‹</button>
                <template v-for="p in getRulesPaginationPages()" :key="p">
                  <span v-if="p === '...'" class="page-ellipsis">…</span>
                  <button
                    v-else
                    class="page-btn"
                    :class="{ active: p === rulesPage }"
                    @click="handleGoToRulesPage(p)">{{ p }}</button>
                </template>
                <button class="page-btn" :disabled="rulesPage >= rulesTotalPages" @click="handleGoToRulesPage(rulesPage + 1)">›</button>
                <span class="page-info">共 {{ rulesTotal }} 条</span>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'model'" class="tab-content">
            <div class="tab-header">
              <h2 class="tab-title">模型版本信息</h2>
            </div>

            <div v-if="isModelLoading" class="loading-container">
              <div class="loading-spinner" ></div>
              <p>正在加载模型信息...</p>
            </div>
            <div v-else-if="modelInfo" class="model-info-grid">
              <div class="model-info-card card">
                <div class="model-info-header">
                  <span class="model-info-icon">🤖</span>
                  <span class="model-info-title">基本信息</span>
                </div>
                <div class="model-info-body">
                  <div class="info-row">
                    <span class="info-label">模型名称</span>
                    <span class="info-value">{{ modelInfo.model_name }}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">版本号</span>
                    <span class="info-value">{{ modelInfo.version }}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">微调时间</span>
                    <span class="info-value">{{ modelInfo.fine_tune_time ? formatTime(modelInfo.fine_tune_time) : '未微调' }}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">备注</span>
                    <span class="info-value">{{ modelInfo.notes || '—' }}</span>
                  </div>
                </div>
              </div>

              <div class="model-metrics-card card">
                <div class="model-info-header">
                  <span class="model-info-icon">📊</span>
                  <span class="model-info-title">评估指标</span>
                </div>
                <div class="metrics-grid">
                  <div class="metric-item">
                    <div class="metric-circle">
                      <svg viewBox="0 0 36 36" class="metric-svg">
                        <path class="metric-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                        <path class="metric-fill metric-fill-blue" :stroke-dasharray="`${modelInfo.metrics.accuracy * 100}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                      </svg>
                      <span class="metric-value">{{ (modelInfo.metrics.accuracy * 100).toFixed(1) }}%</span>
                    </div>
                    <span class="metric-label">准确率</span>
                  </div>
                  <div class="metric-item">
                    <div class="metric-circle">
                      <svg viewBox="0 0 36 36" class="metric-svg">
                        <path class="metric-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                        <path class="metric-fill metric-fill-green" :stroke-dasharray="`${modelInfo.metrics.precision * 100}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                      </svg>
                      <span class="metric-value">{{ (modelInfo.metrics.precision * 100).toFixed(1) }}%</span>
                    </div>
                    <span class="metric-label">精确率</span>
                  </div>
                  <div class="metric-item">
                    <div class="metric-circle">
                      <svg viewBox="0 0 36 36" class="metric-svg">
                        <path class="metric-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                        <path class="metric-fill metric-fill-orange" :stroke-dasharray="`${modelInfo.metrics.recall * 100}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                      </svg>
                      <span class="metric-value">{{ (modelInfo.metrics.recall * 100).toFixed(1) }}%</span>
                    </div>
                    <span class="metric-label">召回率</span>
                  </div>
                  <div class="metric-item">
                    <div class="metric-circle">
                      <svg viewBox="0 0 36 36" class="metric-svg">
                        <path class="metric-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                        <path class="metric-fill metric-fill-purple" :stroke-dasharray="`${modelInfo.metrics.f1_score * 100}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                      </svg>
                      <span class="metric-value">{{ (modelInfo.metrics.f1_score * 100).toFixed(1) }}%</span>
                    </div>
                    <span class="metric-label">F1 分数</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'logs'" class="tab-content">
            <div class="tab-header">
              <h2 class="tab-title">系统日志</h2>
            </div>

            <div class="filter-bar card">
              <div class="filter-item">
                <label class="filter-label" for="log-level">日志级别</label>
                <select id="log-level" v-model="logLevelFilter" class="filter-select">
                  <option v-for="opt in logLevels" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                </select>
              </div>
              <div class="filter-item">
                <label class="filter-label" for="log-search">搜索日志</label>
                <input
                  id="log-search"
                  v-model="logSearch"
                  type="text"
                  class="filter-input"
                  placeholder="按操作内容、用户或消息搜索..."/>
              </div>
            </div>

            <div class="table-card card">
              <div v-if="isLogsLoading" class="table-loading">
                <div class="loading-spinner" ></div>
                <p>正在加载日志数据...</p>
              </div>
              <div v-else-if="logs.length === 0" class="table-empty">
                <div class="empty-icon">📝</div>
                <h3 class="empty-title">暂无日志数据</h3>
                <p class="empty-desc">{{ logSearch || logLevelFilter ? '没有匹配的日志，请调整筛选条件' : '系统运行后将在此显示操作日志' }}</p>
              </div>
              <div v-else class="table-wrapper">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>级别</th>
                      <th>时间</th>
                      <th>操作用户</th>
                      <th>操作内容</th>
                      <th>详细信息</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="log in logs" :key="log.id">
                      <td>
                        <span class="log-badge" :class="getLogLevelClass(log.log_level)">{{ log.log_level }}</span>
                      </td>
                      <td class="cell-time">{{ formatTime(log.created_at) }}</td>
                      <td>{{ log.username }}</td>
                      <td class="cell-action">{{ log.action }}</td>
                      <td class="cell-message">{{ log.message || '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-if="logsTotalPages > 1 && logs.length > 0" class="pagination">
                <button class="page-btn" :disabled="logsPage <= 1" @click="handleGoToLogsPage(logsPage - 1)">‹</button>
                <template v-for="p in getLogsPaginationPages()" :key="p">
                  <span v-if="p === '...'" class="page-ellipsis">…</span>
                  <button
                    v-else
                    class="page-btn"
                    :class="{ active: p === logsPage }"
                    @click="handleGoToLogsPage(p)">{{ p }}</button>
                </template>
                <button class="page-btn" :disabled="logsPage >= logsTotalPages" @click="handleGoToLogsPage(logsPage + 1)">›</button>
                <span class="page-info">共 {{ logsTotal }} 条</span>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'users'" class="tab-content">
            <div class="tab-header">
              <h2 class="tab-title">用户管理</h2>
              <button class="btn btn-primary btn-sm" @click="handleOpenCreateUser">+ 新增用户</button>
            </div>

            <div class="table-card card">
              <div v-if="isUsersLoading" class="table-loading">
                <div class="loading-spinner" ></div>
                <p>正在加载用户数据...</p>
              </div>
              <div v-else-if="users.length === 0" class="table-empty">
                <div class="empty-icon">👤</div>
                <h3 class="empty-title">暂无用户数据</h3>
              </div>
              <div v-else class="table-wrapper">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>用户名</th>
                      <th>角色</th>
                      <th>状态</th>
                      <th>创建时间</th>
                      <th class="col-actions">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="user in users" :key="user.id">
                      <td class="cell-name">{{ user.username }}</td>
                      <td>
                        <span class="role-badge" :class="user.role === 'admin' ? 'role-admin' : 'role-user'">
                          {{ user.role === 'admin' ? '管理员' : '普通用户' }}
                        </span>
                      </td>
                      <td>
                        <span class="status-indicator" :class="user.is_active ? 'status-active' : 'status-inactive'">
                          {{ user.is_active ? '启用' : '禁用' }}
                        </span>
                      </td>
                      <td class="cell-time">{{ formatTime(user.created_at) }}</td>
                      <td class="cell-actions">
                        <button
                          class="btn btn-sm btn-action"
                          :class="user.is_active ? 'btn-action-warning' : 'btn-action-view'"
                          @click="handleToggleUserStatus(user)"
                        >
                          {{ user.is_active ? '禁用' : '启用' }}
                        </button>
                        <button class="btn btn-sm btn-action btn-action-view" @click="handleOpenResetPwd(user)">
                          重置密码
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-if="usersTotalPages > 1 && users.length > 0" class="pagination">
                <button class="page-btn" :disabled="usersPage <= 1" @click="handleGoToUsersPage(usersPage - 1)">‹</button>
                <template v-for="p in getUsersPaginationPages()" :key="p">
                  <span v-if="p === '...'" class="page-ellipsis">…</span>
                  <button
                    v-else
                    class="page-btn"
                    :class="{ active: p === usersPage }"
                    @click="handleGoToUsersPage(p)">{{ p }}</button>
                </template>
                <button class="page-btn" :disabled="usersPage >= usersTotalPages" @click="handleGoToUsersPage(usersPage + 1)">›</button>
                <span class="page-info">共 {{ usersTotal }} 条</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </template>

    <Teleport to="body">
      <div v-if="isRuleDialogVisible" class="dialog-overlay" @click.self="handleCloseRuleDialog">
        <div class="dialog card">
          <div class="dialog-header">
            <h2 class="dialog-title">{{ editingRule ? '编辑规则' : '新增规则' }}</h2>
            <button class="dialog-close" @click="handleCloseRuleDialog">×</button>
          </div>
          <div class="dialog-body">
            <div class="form-group">
              <label class="form-label" for="rule-id">规则ID</label>
              <input
                id="rule-id"
                v-model="ruleForm.rule_id"
                type="text"
                class="form-input"
                :disabled="!!editingRule"
                placeholder="例如: BXXY_11_1"/>
              <span v-if="ruleFormErrors.rule_id" class="form-error">{{ ruleFormErrors.rule_id }}</span>
            </div>
            <div class="form-group">
              <label class="form-label" for="rule-name">规则名称</label>
              <input
                id="rule-name"
                v-model="ruleForm.name"
                type="text"
                class="form-input"
                placeholder="请输入规则名称"/>
              <span v-if="ruleFormErrors.name" class="form-error">{{ ruleFormErrors.name }}</span>
            </div>
            <div class="form-group">
              <label class="form-label" for="rule-desc">描述</label>
              <textarea
                id="rule-desc"
                v-model="ruleForm.description"
                class="form-textarea"
                rows="2"
                placeholder="规则描述"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group form-group-half">
                <label class="form-label" for="rule-source">来源法律</label>
                <input
                  id="rule-source"
                  v-model="ruleForm.source_law"
                  type="text"
                  class="form-input"
                  placeholder="法律名称"/>
              </div>
              <div class="form-group form-group-half">
                <label class="form-label" for="rule-article">条款</label>
                <input
                  id="rule-article"
                  v-model="ruleForm.article"
                  type="text"
                  class="form-input"
                  placeholder="例如: 第十一条第（一）项"/>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="rule-conditions">适用条件（用 | 分隔）</label>
              <input
                id="rule-conditions"
                v-model="ruleForm.conditions"
                type="text"
                class="form-input"
                placeholder="条件1|条件2|条件3"/>
            </div>
            <div class="form-group">
              <label class="form-label" for="rule-conclusion">结论</label>
              <textarea
                id="rule-conclusion"
                v-model="ruleForm.conclusion"
                class="form-textarea"
                rows="2"
                placeholder="规则结论"></textarea>
            </div>
            <div class="form-group">
              <label class="form-label" for="rule-evidence">证据类型（用 | 分隔）</label>
              <input
                id="rule-evidence"
                v-model="ruleForm.evidence_types"
                type="text"
                class="form-input"
                placeholder="证据类型1|证据类型2"/>
            </div>
            <div class="form-group">
              <label class="form-label" for="rule-weight">权重（0-1）</label>
              <input
                id="rule-weight"
                v-model.number="ruleForm.weight"
                type="number"
                class="form-input"
                step="0.05"
                min="0"
                max="1"/>
              <span v-if="ruleFormErrors.weight" class="form-error">{{ ruleFormErrors.weight }}</span>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="btn btn-secondary" @click="handleCloseRuleDialog">取消</button>
            <button class="btn btn-primary" :disabled="isRuleSubmitting" @click="handleSubmitRule">
              {{ isRuleSubmitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="isUserDialogVisible" class="dialog-overlay" @click.self="handleCloseUserDialog">
        <div class="dialog card">
          <div class="dialog-header">
            <h2 class="dialog-title">新增用户</h2>
            <button class="dialog-close" @click="handleCloseUserDialog">×</button>
          </div>
          <div class="dialog-body">
            <div class="form-group">
              <label class="form-label" for="new-username">用户名</label>
              <input
                id="new-username"
                v-model="userForm.username"
                type="text"
                class="form-input"
                placeholder="请输入用户名"/>
              <span v-if="userFormErrors.username" class="form-error">{{ userFormErrors.username }}</span>
            </div>
            <div class="form-group">
              <label class="form-label" for="new-password">密码</label>
              <input
                id="new-password"
                v-model="userForm.password"
                type="password"
                class="form-input"
                placeholder="请输入密码（至少6位）"/>
              <span v-if="userFormErrors.password" class="form-error">{{ userFormErrors.password }}</span>
            </div>
            <div class="form-group">
              <label class="form-label" for="new-role">角色</label>
              <select id="new-role" v-model="userForm.role" class="form-select">
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </select>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="btn btn-secondary" @click="handleCloseUserDialog">取消</button>
            <button class="btn btn-primary" :disabled="isUserSubmitting" @click="handleSubmitUser">
              {{ isUserSubmitting ? '创建中...' : '确认创建' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="isResetPwdDialogVisible" class="dialog-overlay" @click.self="handleCloseResetPwd">
        <div class="dialog dialog-sm card">
          <div class="dialog-header">
            <h2 class="dialog-title">重置密码</h2>
            <button class="dialog-close" @click="handleCloseResetPwd">×</button>
          </div>
          <div class="dialog-body">
            <p class="confirm-text">确定要重置用户「{{ resetPwdTarget?.username }}」的密码吗？</p>
            <div class="form-group" style="margin-top: 1rem;">
              <label class="form-label" for="reset-pwd">新密码</label>
              <input
                id="reset-pwd"
                v-model="resetPwdForm.new_password"
                type="password"
                class="form-input"
                placeholder="请输入新密码（至少6位）"/>
              <span v-if="resetPwdErrors.new_password" class="form-error">{{ resetPwdErrors.new_password }}</span>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="btn btn-secondary" @click="handleCloseResetPwd">取消</button>
            <button class="btn btn-primary" :disabled="isResetPwdSubmitting" @click="handleSubmitResetPwd">
              {{ isResetPwdSubmitting ? '重置中...' : '确认重置' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.settings-page {
  min-height: 100vh;
  background: var(--bg-secondary);
  padding: 2rem 1rem;
}

.settings-header {
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

.unauthenticated {
  max-width: 400px;
  margin: 4rem auto;
  text-align: center;
  padding: 3rem 2rem;
}

.unauth-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.unauthenticated h3 {
  font-size: 1.25rem;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.unauthenticated p {
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
}

.settings-layout {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

.settings-sidebar {
  width: 180px;
  flex-shrink: 0;
  position: sticky;
  top: calc(56px + 2rem);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background: var(--bg-primary);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-md);
  padding: 0.5rem;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem 1rem;
  font-size: 0.9rem;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-secondary);
  background: none;
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
  width: 100%;
}

.sidebar-link:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.sidebar-link.active {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  font-weight: 600;
}

.sidebar-icon {
  font-size: 1.125rem;
  width: 1.5rem;
  text-align: center;
}

.sidebar-label {
  white-space: nowrap;
}

.settings-content {
  flex: 1;
  min-width: 0;
}

.tab-content {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.tab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  gap: 1rem;
}

.tab-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.filter-bar {
  margin-bottom: 1rem;
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
  padding: 1rem 1.25rem;
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
  margin-bottom: 1rem;
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
  padding: 0;
  overflow: hidden;
}

.table-loading {
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
  width: 160px;
}

.cell-rule-id {
  font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
}

.cell-name {
  font-weight: 500;
}

.cell-desc {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}

.cell-time {
  font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.85rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.cell-action {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-message {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.cell-actions {
  text-align: center;
  white-space: nowrap;
}

.weight-badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 100px;
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary);
  border: 1px solid rgba(79, 70, 229, 0.2);
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

.btn-action-warning {
  background: rgba(234, 179, 8, 0.08);
  color: #a16207;
  border-color: rgba(234, 179, 8, 0.2);
}

.btn-action-warning:hover {
  background: var(--color-warning);
  color: white;
  border-color: var(--color-warning);
}

.log-badge {
  display: inline-block;
  padding: 0.2rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 100px;
  white-space: nowrap;
  letter-spacing: 0.03em;
}

.log-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.log-warning {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fde68a;
}

.log-info {
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

.log-debug {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.role-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 100px;
  white-space: nowrap;
}

.role-admin {
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary);
  border: 1px solid rgba(79, 70, 229, 0.2);
}

.role-user {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.status-indicator {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 100px;
  white-space: nowrap;
}

.status-active {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #86efac;
}

.status-inactive {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
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

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  gap: 1rem;
  color: var(--text-secondary);
}

.model-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.model-info-card,
.model-metrics-card {
  padding: 1.5rem;
}

.model-info-header {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-bottom: 1.25rem;
}

.model-info-icon {
  font-size: 1.5rem;
}

.model-info-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.model-info-body {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

.info-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.info-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.info-value {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
  text-align: right;
  max-width: 60%;
  word-break: break-all;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.metric-circle {
  position: relative;
  width: 80px;
  height: 80px;
}

.metric-svg {
  width: 80px;
  height: 80px;
  transform: rotate(-90deg);
}

.metric-bg {
  fill: none;
  stroke: var(--bg-tertiary);
  stroke-width: 3;
}

.metric-fill {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dasharray 0.8s ease;
}

.metric-fill-blue { stroke: var(--color-primary); }
.metric-fill-green { stroke: var(--color-success); }
.metric-fill-orange { stroke: var(--color-warning); }
.metric-fill-purple { stroke: #8b5cf6; }

.metric-value {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-primary);
}

.metric-label {
  font-size: 0.825rem;
  color: var(--text-secondary);
  font-weight: 500;
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

.form-input,
.form-select,
.form-textarea {
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

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.form-textarea {
  resize: vertical;
  line-height: 1.6;
}

.form-select {
  cursor: pointer;
  appearance: auto;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-group-half {
  flex: 1;
}

.form-error {
  display: block;
  margin-top: 0.375rem;
  font-size: 0.8rem;
  color: var(--color-danger);
}

.confirm-text {
  font-size: 0.95rem;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

@media (max-width: 900px) {
  .settings-layout {
    flex-direction: column;
  }

  .settings-sidebar {
    width: 100%;
    position: static;
  }

  .sidebar-nav {
    flex-direction: row;
    overflow-x: auto;
  }

  .sidebar-link {
    white-space: nowrap;
    flex-shrink: 0;
  }

  .model-info-grid {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: 1fr 1fr;
  }

  .form-row {
    flex-direction: column;
    gap: 0;
  }
}

@media (max-width: 768px) {
  .settings-page {
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

  .col-actions {
    width: 140px;
  }

  .metrics-grid {
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .btn-action {
    padding: 0.25rem 0.625rem;
    font-size: 0.75rem;
  }

  .dialog {
    max-width: 100%;
    margin: 0.5rem;
  }
}
</style>
