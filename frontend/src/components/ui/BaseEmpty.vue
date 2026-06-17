<!--
 ============================================================================
 BaseEmpty.vue - BaseEmpty UI 组件
 ============================================================================

 @file BaseEmpty.vue
 @description 帮信罪主观明知智能分析系统 - BaseEmpty UI 组件
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
 * BaseEmpty — 空状态占位组件
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import ResponsiveImage from './ResponsiveImage.vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseEmpty' })

defineProps({
  /** 标题 */
  title: { type: String, default: '暂无数据' },
  /** 描述 */
  description: { type: String, default: '' },
  /** 是否显示图片 */
  showImage: { type: Boolean, default: true },
})

defineEmits(['action'])
</script>

<template>
  <div class="base-empty">
    <ResponsiveImage v-if="showImage" name="empty-state" src-path="/src/assets/images" alt="空状态" class-name="empty-state-image" />
    <p class="empty-title">{{ title }}</p>
    <p v-if="description" class="empty-desc">{{ description }}</p>
    <div v-if="$slots.action" class="empty-action" @click="$emit('action')">
      <slot name="action"></slot>
    </div>
  </div>
</template>

<style scoped>
.base-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-state-image {
  width: 200px;
  height: 200px;
  margin-bottom: 24px;
  opacity: 0.8;
}

.empty-state-image :deep(img) {
  object-fit: contain;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0 0 8px;
}

.empty-desc {
  font-size: 14px;
  color: #6E6E73;
  margin: 0;
  line-height: 1.5;
}

.empty-action {
  margin-top: 24px;
}
</style>
