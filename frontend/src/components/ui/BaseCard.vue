<!--
 ============================================================================
 BaseCard.vue - BaseCard UI 组件
 ============================================================================

 @file BaseCard.vue
 @description 帮信罪主观明知智能分析系统 - BaseCard UI 组件
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
 * BaseCard — 通用卡片容器组件
 *
 * 支持 padding 尺寸、hover 效果、点击模式
 */
defineOptions({ name: 'BaseCard' })

defineProps({
  /** 内边距: sm | md | lg | none */
  padding: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg', 'none'].includes(v),
  },
  /** 是否可点击（显示 hover 效果） */
  clickable: { type: Boolean, default: false },
  /** 是否显示阴影 */
  shadowed: { type: Boolean, default: true },
})

defineEmits(['click'])
</script>

<template>
  <div class="base-card" :class="[ `card-padding-${padding}`, { 'card-clickable': clickable, 'card-shadowed': shadowed }, ]" @click="$emit('click', $event)">
    <slot></slot>
  </div>
</template>

<style scoped>
.base-card {
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: var(--radius-md, 10px);
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.card-shadowed {
  box-shadow: var(--shadow-1);
}

.card-clickable {
  cursor: pointer;
}

.card-clickable:hover {
  transform: translateY(-2px);
  border-color: var(--color-accent-copper, #8b6f47);
  box-shadow: var(--shadow-2);
}

/* ---- Padding ---- */
.card-padding-sm { padding: 12px; }
.card-padding-md { padding: 20px; }
.card-padding-lg { padding: 28px; }
.card-padding-none { padding: 0; }
</style>
