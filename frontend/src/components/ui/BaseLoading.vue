<!--
 ============================================================================
 BaseLoading.vue - BaseLoading UI 组件
 ============================================================================

 @file BaseLoading.vue
 @description 帮信罪主观明知智能分析系统 - BaseLoading UI 组件
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
 * BaseLoading — 通用加载状态组件
 *
 * 支持 spinner 和 skeleton 两种模式
 */
defineOptions({ name: 'BaseLoading' })

defineProps({
  /** 加载模式: spinner | skeleton */
  mode: {
    type: String,
    default: 'spinner',
    validator: (v) => ['spinner', 'skeleton'].includes(v),
  },
  /** 加载文字 */
  text: { type: String, default: '加载中…' },
  /** skeleton 行数（仅 skeleton 模式） */
  rows: { type: Number, default: 3 },
})
</script>

<template> <div class="base-loading" :class="`loading-${mode}`"> <template v-if="mode === 'spinner'">
      <div class="loading-spinner"></div>
      <p v-if="text" class="loading-text">{{ text }}</p>
    </template>

    <!-- Skeleton 模式 -->
    <template v-else>
      <div class="skeleton-blocks">
        <div
          <!-- 列表渲染：i in rows -->
v-for="i in rows"
          :key="i"
          class="skeleton-line"
          :style="{ width: `${85 - i * 10}%` }"
        ></div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.base-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

/* ---- Spinner ---- */
.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border-subtle, #e8e3d9);
  border-top-color: var(--color-accent-copper, #8b6f47);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 12px;
  font-size: 13px;
  color: var(--color-text-tertiary, #aeaeb2);
}

/* ---- Skeleton ---- */
.skeleton-blocks {
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(
    90deg,
    var(--color-border-subtle, #e8e3d9) 25%,
    var(--color-bg-secondary, #faf8f4) 50%,
    var(--color-border-subtle, #e8e3d9) 75%
  );
  background-size: 200% 100%;
  border-radius: 4px;
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
