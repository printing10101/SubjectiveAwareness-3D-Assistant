<!--
 ============================================================================
 BaseDivider.vue - BaseDivider UI 组件
 ============================================================================

 @file BaseDivider.vue
 @description 帮信罪主观明知智能分析系统 - BaseDivider UI 组件
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
 * BaseDivider — 通用分割线组件
 *
 * 支持水平/垂直方向，可带文字
 */
defineOptions({ name: 'BaseDivider' })

defineProps({
  /** 方向: horizontal | vertical */
  direction: {
    type: String,
    default: 'horizontal',
    validator: (v) => ['horizontal', 'vertical'].includes(v),
  },
  /** 文字（仅 horizontal 有效） */
  text: { type: String, default: '' },
  /** 文字位置: left | center | right */
  textPosition: {
    type: String,
    default: 'center',
    validator: (v) => ['left', 'center', 'right'].includes(v),
  },
})
</script>

<template>
  <div v-if="direction === 'horizontal'" class="base-divider divider-horizontal" :class="text ? `text-${textPosition}` : ''">
    <span v-if="text" class="divider-text">{{ text }}</span>
  </div>
  <div v-else class="base-divider divider-vertical"></div>
</template>

<style scoped>
.divider-horizontal {
  display: flex;
  align-items: center;
  width: 100%;
  height: 1px;
  margin: 16px 0;
  background: var(--color-border-subtle, #e8e3d9);
}

.divider-horizontal.text-left,
.divider-horizontal.text-center,
.divider-horizontal.text-right {
  background: none;
  border-top: 1px solid var(--color-border-subtle, #e8e3d9);
}

.divider-text {
  flex-shrink: 0;
  padding: 0 12px;
  font-size: 12px;
  color: var(--color-text-tertiary, #aeaeb2);
  background: var(--color-bg-card, #fff);
}

.text-left .divider-text {
  margin-right: auto;
  padding-left: 0;
}

.text-center .divider-text {
  margin: 0 auto;
}

.text-right .divider-text {
  margin-left: auto;
  padding-right: 0;
}

.divider-vertical {
  display: inline-block;
  width: 1px;
  height: 1em;
  margin: 0 12px;
  background: var(--color-border-subtle, #e8e3d9);
  vertical-align: middle;
}
</style>
