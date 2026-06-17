<!--
 ============================================================================
 BaseTextarea.vue - BaseTextarea UI 组件
 ============================================================================

 @file BaseTextarea.vue
 @description 帮信罪主观明知智能分析系统 - BaseTextarea UI 组件
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
 * BaseTextarea — 多行文本输入组件
 *
 * 支持 label、placeholder、error 状态、disabled、rows
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { ref, computed } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseTextarea' })

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
  /** 行数 */
  rows: { type: [Number, String], default: 4 },
  /** 是否可调整大小 */
  resize: { type: String, default: 'vertical' },
})

// 声明变量: emit
const emit = defineEmits(['update:modelValue'])

// 响应式数据：使用 ref 创建可响应的基础类型数据
const textareaRef = // 定义响应式引用
const null)

// 计算属性：基于响应式数据自动计算并缓存结果
const hasError = computed(() => Boolean(props.error))

// 定义 onInput 方法
function onInput(e) {
  // 向父组件触发自定义事件
  emit('update:modelValue', e.target.value)
}
</script>

<template> <div class="base-textarea-wrapper" :class="{ 'has-error': hasError }">
    <label v-if="label" class="textarea-label">{{ label }}</label>

    <textarea :id="label" ref="textareaRef" :value="modelValue" :placeholder="placeholder" :disabled="disabled" :rows="rows" class="base-textarea" :style="{ resize }" @input="onInput"></textarea>

    <p v-if="hasError" class="textarea-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.base-textarea-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.textarea-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary, #1d1d1f);
}

.base-textarea {
  width: 100%;
  padding: 10px 14px;
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: var(--radius-sm, 6px);
  outline: none;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.base-textarea::placeholder {
  color: var(--color-text-tertiary, #aeaeb2);
}

.base-textarea:hover:not(:disabled) {
  border-color: var(--color-border-strong, #d4cfc2);
}

.base-textarea:focus {
  border-color: var(--color-accent-copper, #8b6f47);
  box-shadow: 0 0 0 3px rgba(139, 111, 71, 0.12);
}

.base-textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--color-bg-secondary, #faf8f4);
}

.has-error .base-textarea {
  border-color: var(--color-error, #b23a2a);
}

.has-error .base-textarea:focus {
  box-shadow: 0 0 0 3px rgba(178, 58, 42, 0.12);
}

.textarea-error {
  font-size: 12px;
  color: var(--color-error, #b23a2a);
  margin: 0;
}
</style>
