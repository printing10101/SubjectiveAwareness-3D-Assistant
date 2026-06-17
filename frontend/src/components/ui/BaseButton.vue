<!--
 ============================================================================
 BaseButton.vue - BaseButton UI 组件
 ============================================================================

 @file BaseButton.vue
 @description 帮信罪主观明知智能分析系统 - BaseButton UI 组件
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
 * BaseButton — 通用按钮组件
 *
 * 变体: primary(近黑色) / secondary(米色+描边) / text(暖色文字) / danger(红色)
 * 尺寸: sm / md / lg
 * 状态: default / hover / active / disabled / loading
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { computed } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseButton' })

// 声明变量: props
const props = defineProps({
  /** 按钮变体 */
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'secondary', 'text', 'danger'].includes(v),
  },
  /** 尺寸 */
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v),
  },
  /** 加载中状态 */
  loading: {
    type: Boolean,
    default: false,
  },
  /** 禁用状态 */
  disabled: {
    type: Boolean,
    default: false,
  },
  /** 是否为块级 */
  block: {
    type: Boolean,
    default: false,
  },
  /** 按钮类型 */
  type: {
    type: String,
    default: 'button',
    validator: (v) => ['button', 'submit', 'reset'].includes(v),
  },
  /** 无障碍标签 */
  ariaLabel: {
    type: String,
    default: '',
  },
  /** 是否展开（用于下拉按钮等） */
  ariaExpanded: {
    type: Boolean,
    default: undefined,
  },
  /** 控制的目标元素 ID */
  ariaControls: {
    type: String,
    default: '',
  },
  /** 按钮标题（用于图标按钮） */
  title: {
    type: String,
    default: '',
  },
})

// 声明变量: emit
const emit = defineEmits(['click'])

// 计算属性：基于响应式数据自动计算并缓存结果
const isDisabled = computed(() => props.disabled || props.loading)

// 定义 handleClick 方法
function handleClick(event) {
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (!isDisabled.value) {
    // 向父组件触发自定义事件
    emit('click', event)
  }
}
</script>

<template>
  <button class="base-btn" :class="[ `btn-${variant}`, `btn-${size}`, { 'btn-loading': loading, 'btn-block': block }, ]" :type="type" :disabled="isDisabled" :aria-label="ariaLabel" :aria-expanded="ariaExpanded" :aria-controls="ariaControls" :aria-busy="loading" :title="title" @click="handleClick">
    <span v-if="loading" class="btn-spinner" aria-hidden="true"></span>
    <span class="btn-content">
      <slot></slot>
    </span>
  </button>
</template>

<style scoped>
.base-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--font-sans);
  font-weight: 500;
  line-height: 1;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
  white-space: nowrap;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  position: relative;
  overflow: hidden;
}

.base-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ---- 尺寸 ---- */
.btn-sm {
  padding: 6px 14px;
  font-size: 13px;
}

.btn-md {
  padding: 10px 20px;
  font-size: 14px;
}

.btn-lg {
  padding: 14px 28px;
  font-size: 16px;
}

.btn-block {
  width: 100%;
}

/* ---- 变体: primary (近黑色背景) ---- */
.btn-primary {
  color: #fff;
  background: #1D1D1F;
  border-color: #1D1D1F;
}

.btn-primary:hover:not(:disabled) {
  background: #2C2C2E;
  border-color: #2C2C2E;
  transform: translateY(-1px);
}

.btn-primary:active:not(:disabled) {
  background: #000000;
  border-color: #000000;
  transform: translateY(0) scale(0.98);
}

/* ---- 变体: secondary (米色背景+描边) ---- */
.btn-secondary {
  color: var(--color-text-primary, #1D1D1F);
  background: var(--color-bg-base, #F5F2EC);
  border-color: var(--color-border-subtle, #E8E3D9);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-bg-secondary, #FAF8F4);
  border-color: var(--color-accent-copper, #8B6F47);
  transform: translateY(-1px);
}

.btn-secondary:active:not(:disabled) {
  background: var(--color-border-subtle, #E8E3D9);
  transform: translateY(0) scale(0.98);
}

/* ---- 变体: text (暖色文字) ---- */
.btn-text {
  color: var(--color-accent-copper, #8B6F47);
  background: transparent;
  border-color: transparent;
  padding-left: 8px;
  padding-right: 8px;
}

.btn-text:hover:not(:disabled) {
  color: var(--color-accent-gold, #B8956A);
  background: rgba(139, 111, 71, 0.08);
}

.btn-text:active:not(:disabled) {
  color: #6B5435;
  background: rgba(139, 111, 71, 0.15);
}

/* ---- 变体: danger (红色背景) ---- */
.btn-danger {
  color: #fff;
  background: var(--color-error, #B23A2A);
  border-color: var(--color-error, #B23A2A);
}

.btn-danger:hover:not(:disabled) {
  background: #C94535;
  border-color: #C94535;
  transform: translateY(-1px);
}

.btn-danger:active:not(:disabled) {
  background: #9A2E20;
  border-color: #9A2E20;
  transform: translateY(0) scale(0.98);
}

/* ---- 加载状态 ---- */
.btn-loading {
  pointer-events: none;
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.btn-secondary .btn-spinner {
  border-color: rgba(29, 29, 31, 0.2);
  border-top-color: var(--color-accent-copper, #8B6F47);
}

.btn-text .btn-spinner {
  border-color: rgba(139, 111, 71, 0.2);
  border-top-color: var(--color-accent-copper, #8B6F47);
}

.btn-content {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
