<!--
 ============================================================================
 BaseSelect.vue - BaseSelect UI 组件
 ============================================================================

 @file BaseSelect.vue
 @description 帮信罪主观明知智能分析系统 - BaseSelect UI 组件
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
 * BaseSelect — 通用下拉选择组件
 *
 * 支持 label、placeholder、disabled、multiple、options
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { computed } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseSelect' })

// 声明变量: props
const props = defineProps({
  /** 绑定值 */
  modelValue: { type: [String, Number, Array], default: '' },
  /** 标签文字 */
  label: { type: String, default: '' },
  /** 占位文字 */
  placeholder: { type: String, default: '请选择' },
  /** 选项列表 [{ label, value }] */
  options: { type: Array, default: () => [] },
  /** 禁用 */
  disabled: { type: Boolean, default: false },
  /** 多选 */
  multiple: { type: Boolean, default: false },
  /** 错误提示 */
  error: { type: String, default: '' },
})

// 声明变量: emit
const emit = defineEmits(['update:modelValue', 'change'])

// 计算属性：基于响应式数据自动计算并缓存结果
const hasError = computed(() => Boolean(props.error))

// 定义 onChange 方法
function onChange(e) {
  // 声明变量: value
  const value = props.multiple
    ? Array.from(e.target.selectedOptions).map(opt => opt.value)
    : e.target.value
  // 向父组件触发自定义事件
  emit('update:modelValue', value)
  // 向父组件触发自定义事件
  emit('change', value)
}
</script>

<template>
  <div class="base-select-wrapper" :class="{ 'has-error': hasError }">
    <label v-if="label" class="select-label">{{ label }}</label>

    <div class="select-container">
      <select :id="label" :value="modelValue" :disabled="disabled" :multiple="multiple" class="base-select" @change="onChange">
        <option v-if="!multiple && placeholder" value="" disabled selected>{{ placeholder }}</option>
        <option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>

      <svg class="select-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </div>

    <p v-if="hasError" class="select-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.base-select-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.select-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary, #1d1d1f);
}

.select-container {
  position: relative;
  display: flex;
  align-items: center;
}

.base-select {
  width: 100%;
  padding: 9px 36px 9px 14px;
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: var(--radius-sm, 6px);
  outline: none;
  cursor: pointer;
  appearance: none;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.base-select:hover:not(:disabled) {
  border-color: var(--color-border-strong, #d4cfc2);
}

.base-select:focus {
  border-color: var(--color-accent-copper, #8b6f47);
  box-shadow: 0 0 0 3px rgba(139, 111, 71, 0.12);
}

.base-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--color-bg-secondary, #faf8f4);
}

.base-select[multiple] {
  padding-right: 14px;
  min-height: 100px;
}

.select-icon {
  position: absolute;
  right: 12px;
  pointer-events: none;
  color: var(--color-text-tertiary, #aeaeb2);
}

.has-error .base-select {
  border-color: var(--color-error, #b23a2a);
}

.has-error .base-select:focus {
  box-shadow: 0 0 0 3px rgba(178, 58, 42, 0.12);
}

.select-error {
  font-size: 12px;
  color: var(--color-error, #b23a2a);
  margin: 0;
}
</style>
