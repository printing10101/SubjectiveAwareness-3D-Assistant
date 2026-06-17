<!--
 ============================================================================
 BaseSkeleton.vue - BaseSkeleton UI 组件
 ============================================================================

 @file BaseSkeleton.vue
 @description 帮信罪主观明知智能分析系统 - BaseSkeleton UI 组件
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
 * BaseSkeleton — 骨架屏组件
 *
 * 支持多种骨架类型和自定义
 */
defineOptions({ name: 'BaseSkeleton' })

defineProps({
  /** 骨架类型: text | card | list | table */
  type: {
    type: String,
    default: 'text',
    validator: (v) => ['text', 'card', 'list', 'table'].includes(v),
  },
  /** 行数（text/list 模式） */
  rows: { type: Number, default: 3 },
  /** 是否显示头像（card 模式） */
  avatar: { type: Boolean, default: false },
  /** 是否显示动画 */
  animated: { type: Boolean, default: true },
})
</script>

<template>
  <div class="base-skeleton" :class="[ `skeleton-${type}`, { 'skeleton-animated': animated } ]"> <template v-if="type === 'text'">
      <div v-for="i in rows" :key="i" class="skeleton-line" :style="{ width: `${100 - (i % 3) * 15}%` }"></div>
    </template>

    <!-- Card 模式 -->
    <template v-else-if="type === 'card'">
      <div
        v-if="avatar"
        class="skeleton-avatar"
      ></div>
      <div class="skeleton-card-content">
        <div class="skeleton-line skeleton-title"></div>
        <div
        v-for="i in rows"
        :key="i"
        class="skeleton-line"
        :style="{ width: `${100 - (i % 3) * 15}%` }"
      ></div>
      </div>
    </template>

    <!-- List 模式 -->
    <template v-else-if="type === 'list'">
      <div
        v-for="i in rows"
        :key="i"
        class="skeleton-list-item"
      >
        <div
          v-if="avatar"
          class="skeleton-avatar-sm"
        ></div>
        <div class="skeleton-list-content">
          <div class="skeleton-line skeleton-title-sm"></div>
          <div class="skeleton-line"></div>
        </div>
      </div>
    </template>

    <!-- Table 模式 -->
    <template v-else-if="type === 'table'">
      <div class="skeleton-table-header">
        <div
          v-for="i in 4"
          :key="i"
          class="skeleton-table-cell"
        ></div>
      </div>
      <div
        v-for="i in rows"
        :key="i"
        class="skeleton-table-row"
      >
        <div
          v-for="j in 4"
          :key="j"
          class="skeleton-table-cell"
        ></div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.base-skeleton {
  width: 100%;
}

.skeleton-line {
  height: 14px;
  border-radius: 4px;
  margin-bottom: 12px;
}

/* 使用全局骨架屏动画类 */
.skeleton-animated .skeleton-line {
  background: linear-gradient(
    90deg,
    var(--color-border-subtle, #e8e3d9) 25%,
    var(--color-bg-secondary, #faf8f4) 50%,
    var(--color-border-subtle, #e8e3d9) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-sweep var(--duration-skeleton, 1.5s) ease-in-out infinite;
}

/* 静态状态（无动画） */
.skeleton-line:not(.skeleton-animated .skeleton-line) {
  background: var(--color-border-subtle, #e8e3d9);
}

.skeleton-title {
  height: 18px;
  width: 40%;
  margin-bottom: 16px;
}

.skeleton-title-sm {
  height: 14px;
  width: 30%;
  margin-bottom: 8px;
}

.skeleton-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(
    90deg,
    var(--color-border-subtle, #e8e3d9) 25%,
    var(--color-bg-secondary, #faf8f4) 50%,
    var(--color-border-subtle, #e8e3d9) 75%
  );
  background-size: 200% 100%;
  margin-right: 16px;
  flex-shrink: 0;
}

.skeleton-animated .skeleton-avatar {
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-avatar-sm {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(
    90deg,
    var(--color-border-subtle, #e8e3d9) 25%,
    var(--color-bg-secondary, #faf8f4) 50%,
    var(--color-border-subtle, #e8e3d9) 75%
  );
  background-size: 200% 100%;
  margin-right: 12px;
  flex-shrink: 0;
}

.skeleton-animated .skeleton-avatar-sm {
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-card {
  display: flex;
}

.skeleton-card-content {
  flex: 1;
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border-subtle, #e8e3d9);
}

.skeleton-list-item:last-child {
  border-bottom: none;
}

.skeleton-list-content {
  flex: 1;
}

.skeleton-table-header {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 2px solid var(--color-border-subtle, #e8e3d9);
}

.skeleton-table-row {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border-subtle, #e8e3d9);
}

.skeleton-table-cell {
  flex: 1;
  height: 14px;
  background: linear-gradient(
    90deg,
    var(--color-border-subtle, #e8e3d9) 25%,
    var(--color-bg-secondary, #faf8f4) 50%,
    var(--color-border-subtle, #e8e3d9) 75%
  );
  background-size: 200% 100%;
  border-radius: 4px;
}

.skeleton-animated .skeleton-table-cell {
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
