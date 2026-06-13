<script setup>
/**
 * 案件标注界面
 *
 * 表格形式展示案件列表，每行可编辑 4 类标签：
 * - d1_tier       维度分档 (一档/二档/三档/四档)
 * - final_verdict 最终定性 (认定帮信/不认定帮信/竞合/无罪/其他)
 * - verdict_subtype 认定子类 (主动核实/仅有流水/被骗开卡/熟人借用/获利明显/供述明知/客观推定/其他)
 * - judicial_era  司法时期 (2019解释/2025意见前/2025意见后)
 */
import { ref, computed, onMounted, watch } from 'vue'

import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import apiClient from '../api/client.js'

// 路由
const router = useRouter()

// ---------------------------------------------------------------------------
// 常量：标签选项
// ---------------------------------------------------------------------------

const D1_TIER_OPTIONS = [
  { value: '', label: '未选择' },
  { value: '一档', label: '一档' },
  { value: '二档', label: '二档' },
  { value: '三档', label: '三档' },
  { value: '四档', label: '四档' },
]

const FINAL_VERDICT_OPTIONS = [
  { value: '', label: '未选择' },
  { value: '认定帮信', label: '认定帮信' },
  { value: '不认定帮信', label: '不认定帮信' },
  { value: '竞合', label: '竞合' },
  { value: '无罪', label: '无罪' },
  { value: '其他', label: '其他' },
]

const VERDICT_SUBTYPE_OPTIONS = [
  { value: '', label: '未选择' },
  { value: '主动核实', label: '主动核实' },
  { value: '仅有流水', label: '仅有流水' },
  { value: '被骗开卡', label: '被骗开卡' },
  { value: '熟人借用', label: '熟人借用' },
  { value: '获利明显', label: '获利明显' },
  { value: '供述明知', label: '供述明知' },
  { value: '客观推定', label: '客观推定' },
  { value: '其他', label: '其他' },
]

const JUDICIAL_ERA_OPTIONS = [
  { value: '', label: '未选择' },
  { value: '2019解释', label: '2019解释' },
  { value: '2025意见前', label: '2025意见前' },
  { value: '2025意见后', label: '2025意见后' },
]

// ---------------------------------------------------------------------------
// 响应式数据
// ---------------------------------------------------------------------------

// 案件列表
const cases = ref([])
const total = ref(0)
const isLoading = ref(false)
const errorMsg = ref(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 搜索/筛选
const searchKeyword = ref('')
const verdictFilter = ref('')
const isLabeledFilter = ref('') // ''/labeled/unlabeled

// 已选择的案件 ID（用于批量操作）
const selectedCaseIds = ref([])

// 批量标注对话框
const isBatchDialogVisible = ref(false)
const batchLabelType = ref('final_verdict')
const batchLabelValue = ref('')

// 详情抽屉
const detailVisible = ref(false)
const currentCase = ref(null)

// 保存中
const savingIds = ref(new Set())
const bulkSaving = ref(false)

// ---------------------------------------------------------------------------
// 计算属性
// ---------------------------------------------------------------------------

const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / pageSize.value))
)

const verdictCount = computed(() => {
  const counts = { '认定帮信': 0, '不认定帮信': 0, '竞合': 0, '无罪': 0, '其他': 0, '未标注': 0 }
  for (const c of cases.value) {
    const fv = c.labels?.final_verdict
    if (fv && counts[fv] !== undefined) {
      counts[fv] += 1
    } else {
      counts['未标注'] += 1
    }
  }
  return counts
})

// ---------------------------------------------------------------------------
// 工具函数
// ---------------------------------------------------------------------------

function isCaseLabeled(c) {
  if (!c || !c.labels) return false
  return Boolean(
    c.labels.d1_tier &&
      c.labels.final_verdict &&
      c.labels.verdict_subtype &&
      c.labels.judicial_era
  )
}

function getLabelOptions(labelType) {
  switch (labelType) {
    case 'd1_tier':
      return D1_TIER_OPTIONS
    case 'final_verdict':
      return FINAL_VERDICT_OPTIONS
    case 'verdict_subtype':
      return VERDICT_SUBTYPE_OPTIONS
    case 'judicial_era':
      return JUDICIAL_ERA_OPTIONS
    default:
      return []
  }
}

function truncate(s, n = 60) {
  if (!s) return ''
  if (s.length <= n) return s
  return s.slice(0, n) + '…'
}

// ---------------------------------------------------------------------------
// 数据加载
// ---------------------------------------------------------------------------

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
    const res = await apiClient.get('/api/cases', { params })
    const items = res.data?.items || res.data?.cases || []

    // 并行加载每个案件的标签
    const withLabels = await Promise.all(
      items.map(async (c) => {
        try {
          const lr = await apiClient.get(`/api/cases/${c.id}/labels`)
          const arr = lr.data || []
          const labels = {}
          for (const lab of arr) {
            labels[lab.label_type] = lab.label_value
          }
          return { ...c, labels }
        } catch (e) {
          return { ...c, labels: {} }
        }
      })
    )

    // 应用前端筛选
    let filtered = withLabels
    if (verdictFilter.value) {
      filtered = filtered.filter(
        (c) => c.labels?.final_verdict === verdictFilter.value
      )
    }
    if (isLabeledFilter.value === 'labeled') {
      filtered = filtered.filter(isCaseLabeled)
    } else if (isLabeledFilter.value === 'unlabeled') {
      filtered = filtered.filter((c) => !isCaseLabeled(c))
    }

    cases.value = filtered
    total.value = res.data?.total ?? withLabels.length
  } catch (err) {
    errorMsg.value = err.message || '加载案件失败'
    cases.value = []
    total.value = 0
  } finally {
    isLoading.value = false
  }
}

watch([searchKeyword, verdictFilter, isLabeledFilter], () => {
  currentPage.value = 1
  fetchCases()
})

watch([currentPage, pageSize], () => {
  fetchCases()
})

// ---------------------------------------------------------------------------
// 单条保存
// ---------------------------------------------------------------------------

async function saveLabels(caseRow) {
  if (!caseRow || !caseRow.id) return
  const labels = caseRow.labels || {}
  const payload = {
    labels: [
      { label_type: 'd1_tier', label_value: labels.d1_tier || '', source: 'manual' },
      { label_type: 'final_verdict', label_value: labels.final_verdict || '', source: 'manual' },
      { label_type: 'verdict_subtype', label_value: labels.verdict_subtype || '', source: 'manual' },
      { label_type: 'judicial_era', label_value: labels.judicial_era || '', source: 'manual' },
    ].filter((x) => x.label_value && x.label_value.length > 0),
  }
  if (payload.labels.length === 0) {
    ElMessage.warning('请至少填写一个标签')
    return
  }

  savingIds.value.add(caseRow.id)
  try {
    await apiClient.post(`/api/cases/${caseRow.id}/labels`, payload)
    ElMessage.success(`案件 ${caseRow.id} 标注已保存`)
  } catch (err) {
    const detail = err.data?.detail?.message || err.message || '保存失败'
    ElMessage.error(`保存失败: ${detail}`)
  } finally {
    savingIds.value.delete(caseRow.id)
  }
}

function isSaving(caseId) {
  return savingIds.value.has(caseId)
}

// ---------------------------------------------------------------------------
// 批量操作
// ---------------------------------------------------------------------------

function handleSelectionChange(ids) {
  selectedCaseIds.value = ids
}

async function handleBatchSave() {
  if (selectedCaseIds.value.length === 0) {
    ElMessage.warning('请先选择案件')
    return
  }
  if (!batchLabelValue.value) {
    ElMessage.warning('请选择标签值')
    return
  }
  bulkSaving.value = true
  let success = 0
  let failed = 0
  for (const id of selectedCaseIds.value) {
    try {
      const row = cases.value.find((c) => c.id === id)
      if (!row) continue
      const merged = { ...(row.labels || {}) }
      merged[batchLabelType.value] = batchLabelValue.value
      const payload = {
        labels: Object.entries(merged)
          .filter(([, v]) => v)
          .map(([label_type, label_value]) => ({
            label_type,
            label_value,
            source: 'manual',
          })),
      }
      await apiClient.post(`/api/cases/${id}/labels`, payload)
      success += 1
    } catch (e) {
      failed += 1
    }
  }
  bulkSaving.value = false
  isBatchDialogVisible.value = false
  ElMessage.success(`批量保存完成: 成功 ${success}，失败 ${failed}`)
  await fetchCases()
}

// ---------------------------------------------------------------------------
// 删除标注
// ---------------------------------------------------------------------------

async function handleClearLabels(caseRow) {
  try {
    await ElMessageBox.confirm(
      `确认删除案件 #${caseRow.id} 的全部标签？`,
      '删除确认',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await apiClient.delete(`/api/cases/${caseRow.id}/labels`)
    caseRow.labels = {}
    ElMessage.success('标签已清空')
  } catch (err) {
    ElMessage.error(err.message || '删除失败')
  }
}

// ---------------------------------------------------------------------------
// 详情
// ---------------------------------------------------------------------------

function handleShowDetail(row) {
  currentCase.value = row
  detailVisible.value = true
}

function handleViewAnalysis(row) {
  router.push({ name: 'caseDetail', params: { id: row.id } })
}

// ---------------------------------------------------------------------------
// 分页
// ---------------------------------------------------------------------------

function handlePageChange(p) {
  if (p < 1 || p > totalPages.value) return
  currentPage.value = p
}

// ---------------------------------------------------------------------------
// 生命周期
// ---------------------------------------------------------------------------

onMounted(() => {
  fetchCases()
})
</script>

<template>
  <div class="labeling-view">
    <header class="lv-header">
      <h2 class="lv-title">案件标注</h2>
      <p class="lv-subtitle">
        为每个案件填写 <b>4 类标签</b>：维度分档 / 最终定性 / 认定子类 / 司法时期
      </p>
    </header>

    <!-- 工具栏 -->
    <section class="lv-toolbar">
      <div class="lv-toolbar-left">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索案件标题"
          clearable
          class="lv-search"
        />
        <el-select v-model="verdictFilter" placeholder="按定性筛选" clearable class="lv-filter">
          <el-option
            v-for="o in FINAL_VERDICT_OPTIONS.filter((x) => x.value)"
            :key="o.value"
            :label="o.label"
            :value="o.value"
          />
        </el-select>
        <el-select v-model="isLabeledFilter" placeholder="标注状态" clearable class="lv-filter">
          <el-option label="已完整标注" value="labeled" />
          <el-option label="未完整标注" value="unlabeled" />
        </el-select>
        <el-button @click="fetchCases" :loading="isLoading">刷新</el-button>
      </div>
      <div class="lv-toolbar-right">
        <el-button
          type="primary"
          :disabled="selectedCaseIds.length === 0"
          @click="isBatchDialogVisible = true"
        >
          批量标注 ({{ selectedCaseIds.length }})
        </el-button>
      </div>
    </section>

    <!-- 统计条 -->
    <section class="lv-stats">
      <span class="stat-pill">
        <span class="dot" style="background: #22c55e" />认定帮信: <b>{{ verdictCount['认定帮信'] }}</b>
      </span>
      <span class="stat-pill">
        <span class="dot" style="background: #ef4444" />不认定帮信: <b>{{ verdictCount['不认定帮信'] }}</b>
      </span>
      <span class="stat-pill">
        <span class="dot" style="background: #f59e0b" />竞合: <b>{{ verdictCount['竞合'] }}</b>
      </span>
      <span class="stat-pill">
        <span class="dot" style="background: #3b82f6" />无罪: <b>{{ verdictCount['无罪'] }}</b>
      </span>
      <span class="stat-pill">
        <span class="dot" style="background: #94a3b8" />未标注: <b>{{ verdictCount['未标注'] }}</b>
      </span>
    </section>

    <!-- 错误提示 -->
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      :closable="false"
      class="lv-alert"
    />

    <!-- 表格 -->
    <section class="lv-table-wrap" v-loading="isLoading">
      <el-table
        :data="cases"
        stripe
        border
        height="auto"
        @selection-change="handleSelectionChange"
        empty-text="无数据"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="标题" min-width="240">
          <template #default="{ row }">
            <a class="lv-link" @click="handleShowDetail(row)">
              {{ truncate(row.title, 40) }}
            </a>
          </template>
        </el-table-column>
        <el-table-column label="描述" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="lv-muted">{{ truncate(row.description, 30) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="维度分档" width="130">
          <template #default="{ row }">
            <el-select
              v-model="row.labels.d1_tier"
              placeholder="选择"
              size="small"
              style="width: 100%"
            >
              <el-option
                v-for="o in D1_TIER_OPTIONS.filter((x) => x.value)"
                :key="o.value"
                :label="o.label"
                :value="o.value"
              />
            </el-select>
          </template>
        </el-table-column>

        <el-table-column label="最终定性" width="150">
          <template #default="{ row }">
            <el-select
              v-model="row.labels.final_verdict"
              placeholder="选择"
              size="small"
              style="width: 100%"
            >
              <el-option
                v-for="o in FINAL_VERDICT_OPTIONS.filter((x) => x.value)"
                :key="o.value"
                :label="o.label"
                :value="o.value"
              />
            </el-select>
          </template>
        </el-table-column>

        <el-table-column label="认定子类" width="140">
          <template #default="{ row }">
            <el-select
              v-model="row.labels.verdict_subtype"
              placeholder="选择"
              size="small"
              style="width: 100%"
            >
              <el-option
                v-for="o in VERDICT_SUBTYPE_OPTIONS.filter((x) => x.value)"
                :key="o.value"
                :label="o.label"
                :value="o.value"
              />
            </el-select>
          </template>
        </el-table-column>

        <el-table-column label="司法时期" width="140">
          <template #default="{ row }">
            <el-select
              v-model="row.labels.judicial_era"
              placeholder="选择"
              size="small"
              style="width: 100%"
            >
              <el-option
                v-for="o in JUDICIAL_ERA_OPTIONS.filter((x) => x.value)"
                :key="o.value"
                :label="o.label"
                :value="o.value"
              />
            </el-select>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              :loading="isSaving(row.id)"
              @click="saveLabels(row)"
            >
              保存
            </el-button>
            <el-dropdown size="small">
              <el-button size="small">
                更多
                <el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="handleViewAnalysis(row)">查看案件</el-dropdown-item>
                  <el-dropdown-item @click="handleClearLabels(row)" divided>
                    清空标签
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 分页 -->
    <footer class="lv-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="handlePageChange"
      />
    </footer>

    <!-- 批量标注对话框 -->
    <el-dialog
      v-model="isBatchDialogVisible"
      title="批量标注"
      width="480px"
    >
      <el-form label-width="100px">
        <el-form-item label="标签类型">
          <el-select v-model="batchLabelType" style="width: 100%">
            <el-option label="维度分档" value="d1_tier" />
            <el-option label="最终定性" value="final_verdict" />
            <el-option label="认定子类" value="verdict_subtype" />
            <el-option label="司法时期" value="judicial_era" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签值">
          <el-select v-model="batchLabelValue" style="width: 100%">
            <el-option
              v-for="o in getLabelOptions(batchLabelType).filter((x) => x.value)"
              :key="o.value"
              :label="o.label"
              :value="o.value"
            />
          </el-select>
        </el-form-item>
        <el-alert
          :title="`将对已选的 ${selectedCaseIds.length} 个案件执行批量标注`"
          type="info"
          show-icon
          :closable="false"
        />
      </el-form>
      <template #footer>
        <el-button @click="isBatchDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="bulkSaving" @click="handleBatchSave">
          确认
        </el-button>
      </template>
    </el-dialog>

    <!-- 案件详情抽屉 -->
    <el-drawer
      v-model="detailVisible"
      :title="`案件 #${currentCase?.id ?? ''}`"
      size="520px"
    >
      <div v-if="currentCase" class="lv-detail">
        <h3>{{ currentCase.title }}</h3>
        <p class="lv-muted">案号：{{ currentCase.description }}</p>
        <el-descriptions :column="1" border size="small" class="lv-desc">
          <el-descriptions-item label="ID">{{ currentCase.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ currentCase.status }}</el-descriptions-item>
          <el-descriptions-item label="维度分档">
            {{ currentCase.labels?.d1_tier || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="最终定性">
            {{ currentCase.labels?.final_verdict || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="认定子类">
            {{ currentCase.labels?.verdict_subtype || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="司法时期">
            {{ currentCase.labels?.judicial_era || '—' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.labeling-view {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.lv-header {
  margin-bottom: 16px;
}
.lv-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
}
.lv-subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.lv-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.lv-toolbar-left,
.lv-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.lv-search {
  width: 240px;
}
.lv-filter {
  width: 160px;
}

.lv-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  font-size: 13px;
  color: var(--text-secondary);
}
.stat-pill .dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.stat-pill b {
  color: var(--text-primary);
  font-weight: 600;
}

.lv-alert {
  margin-bottom: 12px;
}

.lv-table-wrap {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
  margin-bottom: 12px;
}

.lv-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.lv-link {
  color: var(--color-primary);
  cursor: pointer;
}
.lv-link:hover {
  text-decoration: underline;
}
.lv-muted {
  color: var(--text-tertiary);
  font-size: 12px;
}

.lv-detail h3 {
  margin: 0 0 4px;
  font-size: 16px;
}
.lv-desc {
  margin-top: 16px;
}
</style>
