<!--
 ============================================================================
 PageContainer.vue - PageContainer UI 组件
 ============================================================================

 @file PageContainer.vue
 @description 帮信罪主观明知智能分析系统 - PageContainer UI 组件
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
 * PageContainer — 页面内容容器
 *
 * 固定最大宽度 1200px，居中显示，白色背景。
 * 移动端自动减小内边距。
 */
</script>

<!--
 ============================================================================
 PageContainer.vue - 页面容器组件，提供统一的页面内边距和最大宽度约束
 ============================================================================
 
 @file PageContainer.vue
 @description 帮信罪主观明知智能分析系统 - 页面容器组件，提供统一的页面内边距和最大宽度约束
 @version 1.0.0
 @author 帮信罪智能分析系统开发团队
 @copyright 2024-2026 帮信罪智能分析系统
 @license MIT
 
 功能说明：
   - 提供用户交互界面和数据展示功能
 
 技术栈：
   - Vue 3 Composition API
   - Pinia 状态管理
   - Element Plus UI 组件库
   - Axios HTTP 客户端
 
 依赖关系：
   - 父组件：AppLayout
   - 子组件：BaseButton, BaseInput, BaseModal 等基础组件
   - Store：analysisStore, caseStore, authStore
   - API：/api/cases, /api/analyses, /api/knowledge
 
 使用说明：
   - 路由访问：N/A
   - 权限要求：需要登录
   - 数据流向：用户输入 -> API 请求 -> 状态更新 -> 视图渲染
 
 ============================================================================
-->
<template> <div class="page-container">
    <slot></slot>
  </div>
</template>

<style scoped>
.page-container {
  width: 100%;
  max-width: var(--layout-content-max-width, 1200px);
  margin: 0 auto;
  padding: var(--spacing-6, 32px);
  background-color: var(--color-bg-card, #ffffff);
  border-radius: var(--radius-lg, 16px);
  min-height: calc(100vh - 64px - var(--spacing-6, 32px) * 2);
  box-shadow: var(--shadow-1);
}

@media (max-width: 767px) {
  .page-container {
    padding: var(--spacing-4, 16px);
    border-radius: var(--radius-md, 10px);
    min-height: calc(100vh - 56px - var(--spacing-4, 16px) * 2);
  }
}
</style>
