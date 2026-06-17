<!--
 ============================================================================
 AppSidebar.vue - AppSidebar UI 组件
 ============================================================================

 @file AppSidebar.vue
 @description 帮信罪主观明知智能分析系统 - AppSidebar UI 组件
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
 * AppSidebar — 侧边栏导航
 * 桌面端展开显示图标+文字，平板端折叠仅显示图标
 * 6 个标准菜单项，路由激活态带左侧 3px 暖色竖条
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { useRoute, useRouter } from 'vue-router'

// 导入外部依赖模块
import BaseButton from '../ui/BaseButton.vue'

// ----------------------------------------------------------------------------
defineProps({
  collapsed: {
    type: Boolean,
    default: false,
  },
})

// 声明变量: emit
const emit = defineEmits(['toggle'])

// 声明变量: route
const route = useRoute()
// 声明变量: router
const router = useRouter()

// 声明变量: menuItems
const menuItems = [
  { name: 'dashboard', label: '首页', icon: 'home', path: '/dashboard' },
  { name: 'analysis', label: '分析', icon: 'analysis', path: '/analysis' },
  { name: 'report', label: '报告', icon: 'report', path: '/report' },
  { name: 'knowledge', label: '知识', icon: 'knowledge', path: '/knowledge' },
  { name: 'eval', label: '评测', icon: 'eval', path: '/eval' },
  { name: 'settings', label: '我的', icon: 'settings', path: '/settings' },
]

// 定义 isActive 方法
function isActive(item) {
  // 返回处理结果
  return route.name === item.name || route.path.startsWith(item.path)
}

// 定义 navigate 方法
function navigate(item) {
  // 路由导航：跳转到指定页面或路由
router.push(item.path)
}
</script>

<template>
  <aside class="app-sidebar" :class="{ collapsed }">  
<div class="sidebar-brand">
      <span class="brand-icon">&#x2696;&#xFE0F;</span>
      <span v-show="!collapsed" class="brand-text">明知分析</span>
    </div> <nav class="sidebar-nav" role="navigation" aria-label="主导航">
      <BaseButton v-for="item in menuItems" :key="item.name" variant="text" class="sidebar-item" :class="{ active: isActive(item) }" :title="collapsed ? item.label : undefined" :aria-current="isActive(item) ? 'page' : undefined" @click="navigate(item)"> <svg class="sidebar-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"> <template v-if="item.icon === 'home'">
            <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </template>
          <!-- 分析 -->
          <template v-else-if="item.icon === 'analysis'">
            <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </template>
          <!-- 报告 -->
          <template v-else-if="item.icon === 'report'">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </template>
          <!-- 知识 -->
          <template v-else-if="item.icon === 'knowledge'">
            <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </template>
          <!-- 评测 -->
          <template v-else-if="item.icon === 'eval'">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
          </template>
          <!-- 我的 / 设置 -->
          <template v-else-if="item.icon === 'settings'">
            <path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </template>
        </svg>

        <span
          <!-- 条件渲染：!collapsed -->
v-show="!collapsed"
          class="sidebar-label"
        >{{ item.label }}</span>
      </BaseButton>
    </nav>

    <!-- 底部折叠切换按钮 -->
    <div class="sidebar-footer">
      <BaseButton
        variant="text"
        class="collapse-btn"
        :aria-label="collapsed ? '展开侧栏' : '折叠侧栏'"
        <!-- 事件绑定：emit('toggle') -->
@click="emit('toggle')"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          :class="{ rotated: collapsed }"
          aria-hidden="true"
        >
          <path d="M15 18l-6-6 6-6" />
        </svg>
        <span
          <!-- 条件渲染：!collapsed -->
v-show="!collapsed"
          class="collapse-label"
        >收起侧栏</span>
      </BaseButton>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  width: 240px;
  background-color: var(--color-bg-card, #fff);
  border-right: 1px solid var(--color-border-subtle, #e8e3d9);
  transition: width var(--duration-base, 300ms) var(--ease-out, cubic-bezier(0.25, 0.1, 0.25, 1));
  overflow: hidden;
  z-index: 30;
}

.app-sidebar.collapsed {
  width: 60px;
}

/* ---- Logo ---- */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border-subtle, #e8e3d9);
  min-height: 64px;
}

.collapsed .sidebar-brand {
  justify-content: center;
  padding: 16px 0;
}

.brand-icon {
  font-size: 22px;
  flex-shrink: 0;
}

.brand-text {
  font-family: var(--font-serif, 'Noto Serif SC', serif);
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1d1d1f);
  white-space: nowrap;
}

/* ---- 导航菜单 ---- */
.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 14px;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary, #6e6e73);
  background: none;
  border: none;
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out, cubic-bezier(0.25, 0.1, 0.25, 1));
  white-space: nowrap;
  position: relative;
  border-left: 3px solid transparent;
}

.sidebar-item:hover {
  color: var(--color-text-primary, #1d1d1f);
  background-color: var(--color-bg-secondary, #faf8f4);
}

.sidebar-item.active {
  color: var(--color-accent-copper, #8b6f47);
  background-color: rgba(139, 111, 71, 0.08);
  border-left-color: var(--color-accent-copper, #8b6f47);
  font-weight: 600;
}

.collapsed .sidebar-item {
  justify-content: center;
  padding: 10px 0;
}

.sidebar-icon {
  flex-shrink: 0;
}

.sidebar-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- 底部折叠按钮 ---- */
.sidebar-footer {
  padding: 8px;
  border-top: 1px solid var(--color-border-subtle, #e8e3d9);
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 14px;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-tertiary, #aeaeb2);
  background: none;
  border: none;
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.collapse-btn:hover {
  color: var(--color-text-primary, #1d1d1f);
  background-color: var(--color-bg-secondary, #faf8f4);
}

.collapsed .collapse-btn {
  justify-content: center;
  padding: 8px 0;
}

.collapse-label {
  white-space: nowrap;
}

.rotated {
  transform: rotate(180deg);
}
</style>
