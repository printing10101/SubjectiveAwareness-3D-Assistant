<!--
 ============================================================================
 BaseBadge.vue - BaseBadge UI 组件
 ============================================================================

 @file BaseBadge.vue
 @description 帮信罪主观明知智能分析系统 - BaseBadge UI 组件
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
<script setup>
// ============================================================================
// 组件脚本模块 - Script Setup
// ============================================================================
// 使用 Vue 3 Composition API 的 <script setup> 语法糖
// 包含：响应式数据定义、计算属性、方法函数、生命周期钩子
// ============================================================================

/**
 * BaseBadge — 通用徽标/标签组件
 *
 * 变体: default | success | warning | error | accent
 * 尺寸: sm | md
 */
defineOptions({ name: 'BaseBadge' })

defineProps({
  /** 变体: default | success | warning | error | accent */
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'success', 'warning', 'error', 'accent'].includes(v),
  },
  /** 尺寸: sm | md */
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md'].includes(v),
  },
  /** 圆点模式（仅显示小圆点） */
  dot: { type: Boolean, default: false },
})
</script>

<template>
  <span v-if="dot" class="base-badge badge-dot" :class="[`badge-${variant}`, `badge-${size}`]"></span>
  <span v-else class="base-badge" :class="[`badge-${variant}`, `badge-${size}`]">
    <slot></slot>
  </span>
</template>

<style scoped>
.base-badge {
  display: inline-flex;
  align-items: center;
  font-weight: 600;
  white-space: nowrap;
  border-radius: 999px;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

/* ---- 尺寸 ---- */
.badge-sm {
  padding: 2px 8px;
  font-size: 11px;
  line-height: 1.4;
}

.badge-md {
  padding: 3px 10px;
  font-size: 12px;
  line-height: 1.5;
}

/* ---- 变体 ---- */
.badge-default {
  color: var(--color-text-secondary, #6e6e73);
  background: var(--color-bg-secondary, #faf8f4);
}

.badge-success {
  color: #fff;
  background: var(--color-success, #2d7d4a);
}

.badge-warning {
  color: #fff;
  background: var(--color-warning, #b8791e);
}

.badge-error {
  color: #fff;
  background: var(--color-error, #b23a2a);
}

.badge-accent {
  color: #fff;
  background: var(--color-accent-copper, #8b6f47);
}

/* ---- 圆点模式 ---- */
.badge-dot {
  width: 8px;
  height: 8px;
  padding: 0;
  border-radius: 50%;
}

.badge-dot.badge-sm {
  width: 6px;
  height: 6px;
}

.badge-dot.badge-md {
  width: 8px;
  height: 8px;
}
</style>
