<!--
 ============================================================================
 BasePagination.vue - BasePagination UI 组件
 ============================================================================

 @file BasePagination.vue
 @description 帮信罪主观明知智能分析系统 - BasePagination UI 组件
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
 * BasePagination — 通用分页组件
 *
 * 支持页码切换、页大小、总数显示
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { computed } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BasePagination' })

// 声明变量: props
const props = defineProps({
  /** 当前页码 */
  modelValue: { type: Number, default: 1 },
  /** 每页条数 */
  pageSize: { type: Number, default: 10 },
  /** 总条数 */
  total: { type: Number, default: 0 },
  /** 每页条数选项 */
  pageSizeOptions: { type: Array, default: () => [10, 20, 50, 100] },
})

// 声明变量: emit
const emit = defineEmits(['update:modelValue', 'update:pageSize', 'change'])

// 计算属性：基于响应式数据自动计算并缓存结果
const totalPages = computed(() => Math.ceil(props.total / props.pageSize))

// 计算属性：基于响应式数据自动计算并缓存结果
const displayPages = computed(() => {
  // 声明变量: pages
  const pages = []
  // 声明变量: current
  const current = props.modelValue
  // 声明变量: total
  const total = totalPages.value
  
  // 条件分支：根据状态执行不同的业务逻辑

  
  // 条件判断：根据条件执行不同逻辑
  if (total <= 7) {
    // 循环处理：遍历数据集合
    for (let i = 1; i <= total; i++) pages.push(i)
  // 条件不满足时的备选逻辑
  } else {
    // 条件分支：根据状态执行不同的业务逻辑

    // 条件判断：根据条件执行不同逻辑
    if (current <= 4) {
      // 循环处理：遍历数据集合
      for (let i = 1; i <= 5; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    } else // 条件分支：根据状态执行不同的业务逻辑
 if (current >= total - 3) {
      pages.push(1)
      pages.push('...')
      // 循环处理：遍历数据集合
      for (let i = total - 4; i <= total; i++) pages.push(i)
    // 条件不满足时的备选逻辑
    } else {
      pages.push(1)
      pages.push('...')
      // 循环处理：遍历数据集合
      for (let i = current - 1; i <= current + 1; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    }
  }
  
  // 返回处理结果
  return pages
})

// 定义 goToPage 方法
function goToPage(page) {
  // 条件判断：根据条件执行不同逻辑
  if (page === '...' || page < 1 || page > totalPages.value) return
  // 向父组件触发自定义事件
  emit('update:modelValue', page)
  // 向父组件触发自定义事件
  emit('change', page)
}

// 定义 onPageSizeChange 方法
function onPageSizeChange(e) {
  // 声明变量: newSize
  const newSize = Number(e.target.value)
  // 向父组件触发自定义事件
  emit('update:pageSize', newSize)
  // 向父组件触发自定义事件
  emit('update:modelValue', 1)
}

// 计算属性：基于响应式数据自动计算并缓存结果
const startItem = computed(() => props.total === 0 ? 0 : (props.modelValue - 1) * props.pageSize + 1)
// 计算属性：基于响应式数据自动计算并缓存结果
const endItem = computed(() => Math.min(props.modelValue * props.pageSize, props.total))
</script>

<template>
  <div class="base-pagination">
    <div class="pagination-info">
      显示 {{ startItem }}-{{ endItem }} 条，共 {{ total }} 条
    </div>

    <div class="pagination-controls">
      <button class="pagination-btn" :disabled="modelValue <= 1" @click="goToPage(modelValue - 1)">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>

      <template v-for="(page, idx) in displayPages" :key="idx">
        <span v-if="page === '...'" class="pagination-ellipsis">...</span>
        <button v-else class="pagination-btn page-number" :class="{ active: page === modelValue }" @click="goToPage(page)">{{ page }}</button>
      </template>

      <button
        class="pagination-btn"
        :disabled="modelValue >= totalPages"
        @click="goToPage(modelValue + 1)"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>

      <select
        class="page-size-select"
        :value="pageSize"
        @change="onPageSizeChange"
      >
        <option
          v-for="size in pageSizeOptions"
          :key="size"
          :value="size"
        >{{ size }} 条/页</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.base-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 0;
  flex-wrap: wrap;
}

.pagination-info {
  font-size: 13px;
  color: var(--color-text-secondary, #6e6e73);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pagination-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  padding: 0 8px;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.pagination-btn:hover:not(:disabled) {
  border-color: var(--color-accent-copper, #8b6f47);
  color: var(--color-accent-copper, #8b6f47);
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-btn.active {
  background: var(--color-accent-copper, #8b6f47);
  border-color: var(--color-accent-copper, #8b6f47);
  color: #fff;
}

.pagination-ellipsis {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--color-text-tertiary, #aeaeb2);
}

.page-size-select {
  padding: 6px 12px;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: 6px;
  cursor: pointer;
  outline: none;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.page-size-select:hover {
  border-color: var(--color-border-strong, #d4cfc2);
}

.page-size-select:focus {
  border-color: var(--color-accent-copper, #8b6f47);
  box-shadow: 0 0 0 3px rgba(139, 111, 71, 0.12);
}
</style>
