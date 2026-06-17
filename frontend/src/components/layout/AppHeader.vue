<!--
 ============================================================================
 AppHeader.vue - AppHeader UI 组件
 ============================================================================

 @file AppHeader.vue
 @description 帮信罪主观明知智能分析系统 - AppHeader UI 组件
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
 * AppHeader — 顶部导航栏
 *
 * 磨砂玻璃效果，粘性定位。
 * 左侧：折叠按钮 + 面包屑占位
 * 中间：搜索框占位
 * 右侧：通知图标 + 用户头像下拉占位
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { ref } from 'vue'

// 导入外部依赖模块
import BaseButton from '../ui/BaseButton.vue'

// ----------------------------------------------------------------------------
defineProps({
  sidebarCollapsed: {
    type: Boolean,
    default: false,
  },
})

// 声明变量: emit
const emit = defineEmits(['toggle-sidebar'])

// 响应式数据：使用 ref 创建可响应的基础类型数据
const showUserMenu = // 定义响应式引用
const false)

// 定义 toggleUserMenu 方法
function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
}
</script>

<template>
  <header class="app-header"> <div class="header-inner"> <div class="header-left">
        <BaseButton variant="text" class="header-toggle" aria-label="切换侧边栏" @click="emit('toggle-sidebar')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </BaseButton>

        <div class="header-breadcrumb">
          <span class="breadcrumb-placeholder">面包屑占位</span>
        </div>
      </div> <div class="header-center">
        <div class="search-placeholder">
          <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <span class="search-text">搜索案件、法条、知识…</span>
        </div>
      </div> <div class="header-right"> <BaseButton variant="text" class="header-icon-btn" aria-label="通知" title="通知">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 01-3.46 0" />
          </svg>
        </BaseButton> <div class="user-dropdown">
          <BaseButton variant="text" class="user-avatar-btn" aria-label="用户菜单" :aria-expanded="showUserMenu" aria-controls="user-menu" @click="toggleUserMenu">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </BaseButton> <Transition name="dropdown">
            <div v-if="showUserMenu" id="user-menu" class="user-menu" role="menu" aria-label="用户菜单">
              <div class="user-menu-header">
                <span class="user-menu-name">管理员</span>
                <span class="user-menu-role">admin</span>
              </div>
              <div class="user-menu-divider"></div>
              <BaseButton variant="text" class="user-menu-item" role="menuitem">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" /></svg>
                个人设置
              </BaseButton>
              <BaseButton variant="text" class="user-menu-item" role="menuitem">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
                退出登录
              </BaseButton>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background-color: var(--color-bg-glass, rgba(245, 242, 236, 0.85));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border-subtle, #e8e3d9);
  height: 64px;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 var(--spacing-5, 24px);
  gap: var(--spacing-4, 16px);
}

/* ---- 左侧 ---- */
.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-3, 12px);
  flex-shrink: 0;
}

.header-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  color: var(--color-text-secondary, #6e6e73);
  background: none;
  border: none;
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.header-toggle:hover {
  color: var(--color-text-primary, #1d1d1f);
  background-color: var(--color-bg-secondary, #faf8f4);
}

.header-breadcrumb {
  display: flex;
  align-items: center;
}

.breadcrumb-placeholder {
  font-size: 13px;
  color: var(--color-text-tertiary, #aeaeaeb2);
}

/* ---- 中间 ---- */
.header-center {
  flex: 1;
  max-width: 480px;
  display: flex;
  justify-content: center;
}

.search-placeholder {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: 360px;
  padding: 8px 14px;
  background-color: var(--color-bg-secondary, #faf8f4);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: var(--radius-md, 10px);
  color: var(--color-text-tertiary, #aeaeaeb2);
  font-size: 13px;
  cursor: text;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.search-placeholder:hover {
  border-color: var(--color-border-strong, #d4cfc2);
}

.search-icon {
  flex-shrink: 0;
  opacity: 0.6;
}

.search-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- 右侧 ---- */
.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-2, 8px);
  flex-shrink: 0;
}

.header-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  color: var(--color-text-secondary, #6e6e73);
  background: none;
  border: none;
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.header-icon-btn:hover {
  color: var(--color-text-primary, #1d1d1f);
  background-color: var(--color-bg-secondary, #faf8f4);
}

/* ---- 用户下拉 ---- */
.user-dropdown {
  position: relative;
}

.user-avatar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  color: var(--color-text-secondary, #6e6e73);
  background: var(--color-bg-secondary, #faf8f4);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: 50%;
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.user-avatar-btn:hover {
  color: var(--color-text-primary, #1d1d1f);
  border-color: var(--color-accent-copper, #8b6f47);
}

.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 180px;
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--shadow-3);
  z-index: 50;
  overflow: hidden;
}

.user-menu-header {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-menu-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1d1d1f);
}

.user-menu-role {
  font-size: 12px;
  color: var(--color-text-tertiary, #aeaeaeb2);
}

.user-menu-divider {
  height: 1px;
  background: var(--color-border-subtle, #e8e3d9);
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-sans);
  color: var(--color-text-secondary, #6e6e73);
  background: none;
  border: none;
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.user-menu-item:hover {
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-secondary, #faf8f4);
}

/* 下拉动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 200ms var(--ease-out);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ---- 移动端响应式 ---- */
@media (max-width: 767px) {
  .app-header {
    height: 56px;
  }

  .header-inner {
    padding: 0 var(--spacing-4, 16px);
  }

  .header-breadcrumb {
    display: none;
  }

  .header-center {
    display: none;
  }
}
</style>
