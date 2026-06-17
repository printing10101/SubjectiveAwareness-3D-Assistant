<!--
 ============================================================================
 AppLayout.vue - AppLayout UI 组件
 ============================================================================

 @file AppLayout.vue
 @description 帮信罪主观明知智能分析系统 - AppLayout UI 组件
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
 * AppLayout — 三档响应式布局容器
 *
 * 桌面端 (≥1280px) : 侧边栏 240px + 顶栏 64px + 主内容
 * 平板端 (768–1279px): 侧边栏折叠 60px + 顶栏 64px + 主内容
 * 移动端 (<768px)   : 顶栏 56px + 主内容 + 底部 Tab 栏 60px
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { ref, provide } from 'vue'

// 导入外部依赖模块
import AppHeader from './AppHeader.vue'
// 导入外部依赖模块
import AppSidebar from './AppSidebar.vue'
// 导入外部依赖模块
import MobileTabbar from './MobileTabbar.vue'

// ----------------------------------------------------------------------------
// 响应式数据：使用 ref 创建可响应的基础类型数据
const sidebarCollapsed = // 定义响应式引用
const false)

// 定义 toggleSidebar 方法
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

provide('sidebarCollapsed', sidebarCollapsed)
</script>

<template> <div class="app-layout"> <AppSidebar class="layout-sidebar" :collapsed="sidebarCollapsed" @toggle="toggleSidebar" /> <div class="layout-main">
      <AppHeader class="layout-header" :sidebar-collapsed="sidebarCollapsed" @toggle-sidebar="toggleSidebar" />

      <main class="layout-content">
        <slot></slot>
      </main>
    </div> <MobileTabbar class="layout-tabbar" />
  </div>
</template>

<style scoped>
.app-layout {
  display: grid;
  min-height: 100vh;
  background-color: var(--color-bg-base, #f5f2ec);
}

/* =====================================================
 * 桌面端 (≥1280px)
 * ===================================================== */
@media (min-width: 1280px) {
  .app-layout {
    grid-template-columns: 240px 1fr;
    grid-template-rows: 64px 1fr;
  }

  .layout-sidebar {
    grid-row: 1 / -1;
  }

  .layout-main {
    grid-column: 2;
    grid-row: 1 / -1;
    display: flex;
    flex-direction: column;
  }

  .layout-tabbar {
    display: none;
  }
}

/* =====================================================
 * 平板端 (768px – 1279px)
 * ===================================================== */
@media (min-width: 768px) and (max-width: 1279px) {
  .app-layout {
    grid-template-columns: 60px 1fr;
    grid-template-rows: 64px 1fr;
  }

  .layout-sidebar {
    grid-row: 1 / -1;
  }

  .layout-main {
    grid-column: 2;
    grid-row: 1 / -1;
    display: flex;
    flex-direction: column;
  }

  .layout-tabbar {
    display: none;
  }
}

/* =====================================================
 * 移动端 (<768px)
 * ===================================================== */
@media (max-width: 767px) {
  .app-layout {
    grid-template-columns: 1fr;
    grid-template-rows: 56px 1fr 60px;
  }

  .layout-sidebar {
    display: none;
  }

  .layout-main {
    grid-column: 1;
    grid-row: 2;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .layout-content {
    flex: 1;
  }

  .layout-tabbar {
    display: flex;
  }
}

/* =====================================================
 * 内容区通用
 * ===================================================== */
.layout-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-6, 32px);
}

@media (max-width: 767px) {
  .layout-content {
    padding: var(--spacing-4, 16px);
    padding-bottom: 0;
  }
}
</style>
