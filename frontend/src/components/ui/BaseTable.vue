<!--
 ============================================================================
 BaseTable.vue - BaseTable UI 组件
 ============================================================================

 @file BaseTable.vue
 @description 帮信罪主观明知智能分析系统 - BaseTable UI 组件
 @version 1.0.0
 @author 帮信罪智能分析系统开发团队
 @copyright 2024-2026 帮信罪智能分析系统

 功能说明：
   - 可复用界面元素、属性配置、事件处理、样式定制
   - 数据绑定和响应式更新
   - 用户交互事件处理
   - 组件生命周期管理

 技术栈：
   - Vue 3 Composition API
   - Pinia 状态管理
   - Element Plus UI 组件库
   - Axios HTTP 客户端

 依赖关系：
   - 父组件：AppLayout 或路由视图
   - 子组件：BaseButton, BaseInput, BaseModal 等基础组件
   - Store：analysisStore, caseStore, authStore
   - API：/api/cases, /api/analyses, /api/knowledge

 使用说明：
   - 路由访问：通过 Vue Router 配置的路径访问
   - 权限要求：需要用户登录后访问
   - 数据流向：用户输入 -> API 请求 -> 状态更新 -> 视图渲染

 ============================================================================
-->
<script setup>// 导入依赖模块和组件

// ============================================================================
// 组件脚本模块 - Script Setup
// ============================================================================
// 使用 Vue 3 Composition API 的 <script setup> 语法糖
// 包含：响应式数据定义、计算属性、方法函数、生命周期钩子
// ============================================================================

/**
 * BaseTable — 通用表格组件
 *
 * 支持列定义、排序、分页、空状态
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { computed } from 'vue'

// 导入外部依赖模块
import BaseEmpty from './BaseEmpty.vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseTable' })

// 声明变量: props
const props = defineProps({
  /** 列定义 [{ key, label, width, sortable }] */
  columns: { type: Array, default: () => [] },
  /** 数据行 */
  data: { type: Array, default: () => [] },
  /** 排序字段 */
  sortBy: { type: String, default: '' },
  /** 排序方向: asc | desc */
  sortOrder: { type: String, default: 'asc' },
  /** 加载中 */
  loading: { type: Boolean, default: false },
  /** 空状态文字 */
  emptyText: { type: String, default: '暂无数据' },
})

// 声明变量: emit
const emit = defineEmits(['sort', 'row-click'])

// 计算属性：基于响应式数据自动计算并缓存结果
const isEmpty = computed(() => !props.loading && props.data.length === 0)

// 定义 onSort 方法
function onSort(column) {
  // 条件判断：根据条件执行不同逻辑
  if (!column.sortable) return
  // 声明变量: newOrder
  const newOrder = props.sortBy === column.key && props.sortOrder === 'asc' ? 'desc' : 'asc'
  // 向父组件触发自定义事件
  emit('sort', { sortBy: column.key, sortOrder: newOrder })
}

// 定义 onRowClick 方法
function onRowClick(row, index) {
  // 向父组件触发自定义事件
  emit('row-click', row, index)
}

// 定义 getSortIcon 方法
function getSortIcon(column) {
  // 条件判断：根据条件执行不同逻辑
  if (!column.sortable) return ''
  // 条件判断：根据条件执行不同逻辑
  if (props.sortBy !== column.key) return '↕'
  // 返回处理结果
  return props.sortOrder === 'asc' ? '↑' : '↓'
}
</script>

<template> <div class="base-table-wrapper">
    <div class="base-table-container" :class="{ 'is-loading': loading }">
      <table class="base-table">
        <thead v-if="columns.length> 0">
          <tr
            <th v-for="col in columns" :key="col.key" :style="{ width: col.width }" :class="{ sortable: col.sortable, sorted: sortBy === col.key }" @click="onSort(col)">
              <span class="th-content">
                {{ col.label }}
                <span v-if="col.sortable" class="sort-icon">{{ getSortIcon(col) }}</span>
              </span>
            </th>
          </tr>
        </thead>
        <tbody
          <tr v-for="(row, index) in data" :key="index" class="table-row" @click="onRowClick(row, index)">
            <td v-for="col in columns" :key="col.key">
              <slot :name="col.key" :row="row" :index="index">
                {{ row[col.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="loading" class="table-loading-overlay">
        <div class="table-loading-spinner"></div>
      </div>

      <BaseEmpty v-if="isEmpty" :title="emptyText" />
    </div>
  </div>
</template>

<style scoped>
.base-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.base-table-container {
  position: relative;
  min-height: 100px;
}

.base-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-sans);
  font-size: 14px;
}

.base-table thead {
  background: var(--color-bg-secondary, #faf8f4);
  border-bottom: 1px solid var(--color-border-subtle, #e8e3d9);
}

.base-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: var(--color-text-primary, #1d1d1f);
  white-space: nowrap;
}

.base-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast, 150ms) var(--ease-out);
}

.base-table th.sortable:hover {
  background: var(--color-border-subtle, #e8e3d9);
}

.base-table th.sorted {
  color: var(--color-accent-copper, #8b6f47);
}

.th-content {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sort-icon {
  font-size: 12px;
  opacity: 0.6;
}

.base-table td {
  padding: 12px 16px;
  color: var(--color-text-primary, #1d1d1f);
  border-bottom: 1px solid var(--color-border-subtle, #e8e3d9);
}

.table-row {
  transition: background var(--duration-fast, 150ms) var(--ease-out);
  cursor: pointer;
}

.table-row:hover {
  background: var(--color-bg-secondary, #faf8f4);
}

.table-row:last-child td {
  border-bottom: none;
}

.table-loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(2px);
}

.table-loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border-subtle, #e8e3d9);
  border-top-color: var(--color-accent-copper, #8b6f47);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
