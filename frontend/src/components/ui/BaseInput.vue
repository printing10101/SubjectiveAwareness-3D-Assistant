<!--
 ============================================================================
 BaseInput.vue - BaseInput UI 组件
 ============================================================================

 @file BaseInput.vue
 @description 帮信罪主观明知智能分析系统 - BaseInput UI 组件
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
 * BaseInput — 通用输入框组件
 *
 * 支持 label、placeholder、error 状态、disabled、clearable
 * 可访问性：aria-invalid、aria-describedby、label 关联
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { ref, computed } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseInput' })

// 声明变量: props
const props = defineProps({
  /** 绑定值 */
  modelValue: { type: String, default: '' },
  /** 标签文字 */
  label: { type: String, default: '' },
  /** 占位文字 */
  placeholder: { type: String, default: '' },
  /** 错误提示 */
  error: { type: String, default: '' },
  /** 禁用 */
  disabled: { type: Boolean, default: false },
  /** 显示清除按钮 */
  clearable: { type: Boolean, default: false },
  /** 输入类型: text | password | email | number */
  type: { type: String, default: 'text' },
  /** 自定义 ID（用于 label/input 关联） */
  id: { type: String, default: '' },
})

// 声明变量: emit
const emit = defineEmits(['update:modelValue', 'clear'])

// 响应式数据：使用 ref 创建可响应的基础类型数据
const inputRef = ref(null)

// 计算属性：基于响应式数据自动计算并缓存结果
const hasError = computed(() => Boolean(props.error))

// 生成唯一 ID 用于 label 和 input 关联
// 计算属性：基于响应式数据自动计算并缓存结果
const inputId = computed(() => props.id || (props.label ? `input-${props.label.replace(/\s+/g, '-').toLowerCase()}` : ''))
// 计算属性：基于响应式数据自动计算并缓存结果
const errorId = computed(() => `${inputId.value}-error`)

// 定义 onInput 方法
function onInput(e) {
  // 向父组件触发自定义事件
  emit('update:modelValue', e.target.value)
}

// 定义 onClear 方法
function onClear() {
  // 向父组件触发自定义事件
  emit('update:modelValue', '')
  // 向父组件触发自定义事件
  emit('clear')
  inputRef.value?.focus()
}
</script>

<template>
  <div class="base-input-wrapper" :class="{ 'has-error': hasError }">
    <label v-if="label" :for="inputId" class="input-label">{{ label }}</label>

    <div class="input-container">
      <input :id="inputId" ref="inputRef" :type="type" :value="modelValue" :placeholder="placeholder" :disabled="disabled" class="base-input" :aria-invalid="hasError" :aria-describedby="hasError ? errorId : undefined" @input="onInput" />

      <button v-if="clearable && modelValue && !disabled" class="input-clear" tabindex="-1" :aria-label="'清除输入'" @click="onClear">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </div>

    <p v-if="hasError" :id="errorId" class="input-error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.base-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary, #1d1d1f);
}

.input-container {
  position: relative;
  display: flex;
  align-items: center;
}

.base-input {
  width: 100%;
  padding: 9px 14px;
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: var(--radius-sm, 6px);
  outline: none;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.base-input::placeholder {
  color: var(--color-text-tertiary, #aeaeb2);
}

.base-input:hover:not(:disabled) {
  border-color: var(--color-border-strong, #d4cfc2);
}

.base-input:focus {
  border-color: #FF9500;
  box-shadow: 0 0 0 3px rgba(255, 149, 0, 0.15);
}

.base-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--color-bg-secondary, #faf8f4);
}

.has-error .base-input {
  border-color: var(--color-error, #b23a2a);
}

.has-error .base-input:focus {
  box-shadow: 0 0 0 3px rgba(178, 58, 42, 0.12);
}

.input-clear {
  position: absolute;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  color: var(--color-text-tertiary, #aeaeb2);
  background: none;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.input-clear:hover {
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-secondary, #faf8f4);
}

.input-error {
  font-size: 12px;
  color: var(--color-error, #b23a2a);
  margin: 0;
}
</style>
