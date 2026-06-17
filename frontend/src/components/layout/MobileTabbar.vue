<!--
 ============================================================================
 MobileTabbar.vue - MobileTabbar UI 组件
 ============================================================================

 @file MobileTabbar.vue
 @description 帮信罪主观明知智能分析系统 - MobileTabbar UI 组件
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
 * MobileTabbar — 移动端底部 Tab 栏
 * 仅在 <768px 显示，高度 60px，含 safe-area 适配
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { useRoute, useRouter } from 'vue-router'

// 导入外部依赖模块
import BaseButton from '../ui/BaseButton.vue'

// ----------------------------------------------------------------------------
const route = useRoute()
// 声明变量: router
const router = useRouter()

// 声明变量: tabs
const tabs = [
  { name: 'dashboard', label: '首页', path: '/dashboard', icon: 'home' },
  { name: 'analysis', label: '分析', path: '/analysis', icon: 'analysis' },
  { name: 'report', label: '报告', path: '/report', icon: 'report' },
  { name: 'settings', label: '我的', path: '/settings', icon: 'user' },
]

// 定义 isActive 方法
function isActive(tab) {
  // 返回处理结果
  return route.name === tab.name || route.path.startsWith(tab.path)
}

// 定义 onTabClick 方法
function onTabClick(tab) {
  // 路由导航：跳转到指定页面或路由
router.push(tab.path)
}
</script>

<template>
  <nav class="mobile-tabbar">
    <BaseButton v-for="tab in tabs" :key="tab.name" variant="text" class="tab-item" :class="{ active: isActive(tab) }" @click="onTabClick(tab)"> <svg class="tab-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"> <template v-if="tab.icon === 'home'">
          <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </template>
        <!-- 分析 -->
        <template v-else-if="tab.icon === 'analysis'">
          <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </template>
        <!-- 报告 -->
        <template v-else-if="tab.icon === 'report'">
          <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </template>
        <!-- 用户 -->
        <template v-else-if="tab.icon === 'user'">
          <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </template>
      </svg>
      <span class="tab-label">{{ tab.label }}</span>
    </BaseButton>
  </nav>
</template>

<style scoped>
.mobile-tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: 60px;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  background-color: var(--color-bg-card, #fff);
  border-top: 1px solid var(--color-border-subtle, #e8e3d9);
  box-shadow: 0 -1px 8px rgba(0, 0, 0, 0.04);
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 48px;
  min-height: 48px;
  padding: 4px 12px;
  font-family: var(--font-sans);
  background: none;
  border: none;
  color: var(--color-text-tertiary, #aeaeaeb2);
  cursor: pointer;
  transition: color var(--duration-fast, 150ms) var(--ease-out);
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}

.tab-item.active {
  color: var(--color-accent-copper, #8b6f47);
}

.tab-icon {
  display: block;
}

.tab-label {
  font-size: 11px;
  font-weight: 500;
  line-height: 1;
}
</style>
