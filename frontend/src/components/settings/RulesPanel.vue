<script setup>
import { ref, computed, watch } from 'vue'

import axios from 'axios'

const props = defineProps({
  errorMsg: {
    type: Object,
    default: () => ({ value: null }),
  },
})

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
    props.errorMsg.value = err.message || '获取规则列表失败'
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
    props.errorMsg.value = err.message || '保存规则失败'
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
    props.errorMsg.value = err.message || '删除规则失败'
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

defineExpose({
  fetchRules,
  rules,
  rulesTotal,
  rulesPage,
  rulesPageSize,
  rulesSearch,
  isRulesLoading,
  rulesTotalPages,
  handleOpenCreateRule,
  handleOpenEditRule,
  handleCloseRuleDialog,
  handleSubmitRule,
  handleDeleteRule,
  handleGoToRulesPage,
  getRulesPaginationPages,
  ruleForm,
  ruleFormErrors,
  isRuleDialogVisible,
  editingRule,
  isRuleSubmitting,
})
</script>

<template>
  <div class="rules-panel">
    <div class="panel-header">
      <h3 class="panel-title">法律规则管理</h3>
      <button class="btn btn-primary btn-sm" @click="handleOpenCreateRule">
        <span class="btn-icon">+</span>
        新建规则
      </button>
    </div>

    <div class="search-bar">
      <input
        v-model="rulesSearch"
        type="text"
        class="search-input"
        placeholder="搜索规则..."
      />
    </div>

    <div v-if="isRulesLoading" class="loading-state">加载中...</div>

    <div v-else class="rules-list">
      <div v-for="rule in rules" :key="rule.id" class="rule-card card">
        <div class="rule-header">
          <div class="rule-title">
            <span class="rule-id">{{ rule.rule_id }}</span>
            <span class="rule-name">{{ rule.name }}</span>
          </div>
          <div class="rule-actions">
            <button class="btn btn-ghost btn-sm" @click="handleOpenEditRule(rule)">
              编辑
            </button>
            <button class="btn btn-danger btn-sm" @click="handleDeleteRule(rule)">
              删除
            </button>
          </div>
        </div>
        <div class="rule-body">
          <div v-if="rule.description" class="rule-desc">{{ rule.description }}</div>
          <div class="rule-meta">
            <span v-if="rule.source_law" class="meta-item">
              <span class="meta-label">来源：</span>{{ rule.source_law }}
            </span>
            <span v-if="rule.article" class="meta-item">
              <span class="meta-label">条款：</span>{{ rule.article }}
            </span>
            <span class="meta-item">
              <span class="meta-label">权重：</span>{{ rule.weight }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="rules.length === 0" class="empty-state">
        <p>暂无规则</p>
      </div>
    </div>

    <div v-if="rulesTotalPages > 1" class="pagination">
      <button
        class="pagination-btn"
        :disabled="rulesPage === 1"
        @click="handleGoToRulesPage(rulesPage - 1)"
      >
        ‹
      </button>
      <button
        v-for="page in getRulesPaginationPages()"
        :key="page"
        class="pagination-btn"
        :class="{ active: page === rulesPage, disabled: page === '...' }"
        :disabled="page === '...'"
        @click="handleGoToRulesPage(page)"
      >
        {{ page }}
      </button>
      <button
        class="pagination-btn"
        :disabled="rulesPage === rulesTotalPages"
        @click="handleGoToRulesPage(rulesPage + 1)"
      >
        ›
      </button>
    </div>

    <!-- 规则编辑对话框 -->
    <div v-if="isRuleDialogVisible" class="dialog-overlay" @click.self="handleCloseRuleDialog">
      <div class="dialog-content card">
        <div class="dialog-header">
          <h3 class="dialog-title">{{ editingRule ? '编辑规则' : '新建规则' }}</h3>
          <button class="dialog-close" @click="handleCloseRuleDialog">×</button>
        </div>
        <form @submit.prevent="handleSubmitRule" class="dialog-body">
          <div class="form-group">
            <label class="form-label">规则ID</label>
            <input v-model="ruleForm.rule_id" type="text" class="form-input" :disabled="!!editingRule" />
            <span v-if="ruleFormErrors.rule_id" class="form-error">{{ ruleFormErrors.rule_id }}</span>
          </div>
          <div class="form-group">
            <label class="form-label">规则名称</label>
            <input v-model="ruleForm.name" type="text" class="form-input" />
            <span v-if="ruleFormErrors.name" class="form-error">{{ ruleFormErrors.name }}</span>
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea v-model="ruleForm.description" class="form-textarea" rows="3"></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">来源法律</label>
              <input v-model="ruleForm.source_law" type="text" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">条款</label>
              <input v-model="ruleForm.article" type="text" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">条件（用 | 分隔多个条件）</label>
            <textarea v-model="ruleForm.conditions" class="form-textarea" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">结论</label>
            <textarea v-model="ruleForm.conclusion" class="form-textarea" rows="2"></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">证据类型（用 | 分隔）</label>
            <input v-model="ruleForm.evidence_types" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">权重（0-1）</label>
            <input v-model.number="ruleForm.weight" type="number" step="0.1" min="0" max="1" class="form-input" />
            <span v-if="ruleFormErrors.weight" class="form-error">{{ ruleFormErrors.weight }}</span>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-ghost" @click="handleCloseRuleDialog">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="isRuleSubmitting">
              {{ isRuleSubmitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rules-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: var(--text-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.search-bar {
  display: flex;
  gap: var(--space-2);
}

.search-input {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.loading-state,
.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-tertiary);
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.rule-card {
  padding: var(--space-4);
}

.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-3);
}

.rule-title {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.rule-id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.rule-name {
  font-size: var(--text-base);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.rule-actions {
  display: flex;
  gap: var(--space-2);
}

.rule-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.rule-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

.rule-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.meta-label {
  color: var(--text-tertiary);
}

.pagination {
  display: flex;
  justify-content: center;
  gap: var(--space-1);
  margin-top: var(--space-4);
}

.pagination-btn {
  padding: var(--space-1) var(--space-2);
  min-width: 32px;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.pagination-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: var(--border-secondary);
}

.pagination-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.dialog-content {
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-primary);
}

.dialog-title {
  font-size: var(--text-lg);
  font-weight: var(--font-weight-semibold);
  margin: 0;
}

.dialog-close {
  background: none;
  border: none;
  font-size: var(--text-2xl);
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
}

.dialog-close:hover {
  background: var(--bg-secondary);
}

.dialog-body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-label {
  font-size: var(--text-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.form-input,
.form-textarea {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-family: inherit;
}

.form-input:disabled {
  background: var(--bg-secondary);
  cursor: not-allowed;
}

.form-textarea {
  resize: vertical;
}

.form-error {
  font-size: var(--text-xs);
  color: var(--color-danger);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-primary);
}
</style>
