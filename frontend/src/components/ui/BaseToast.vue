<!--
 ============================================================================
 BaseToast.vue - BaseToast UI 组件
 ============================================================================

 @file BaseToast.vue
 @description 帮信罪主观明知智能分析系统 - BaseToast UI 组件
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
 * BaseToast — 通用消息提示组件
 *
 * 支持 success/error/warning/info 类型
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { ref } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseToast' })

// 响应式数据：使用 ref 创建可响应的基础类型数据
const toasts = // 定义响应式引用
const [])
// 声明变量: toastId
let toastId = 0

// 定义 show 方法
function show(options) {
  // 声明变量: id
  const id = ++toastId
  // 声明变量: toast
  const toast = {
    id,
    type: options.type || 'info',
    message: options.message || '',
    duration: options.duration !== undefined ? options.duration : 3000,
  }
  
  toasts.value.push(toast)
  
  // 条件分支：根据状态执行不同的业务逻辑

  
  // 条件判断：根据条件执行不同逻辑
  if (toast.duration > 0) {
    setTimeout(() => {
      remove(id)
    }, toast.duration)
  }
  
  // 返回处理结果
  return id
}

// 定义 remove 方法
function remove(id) {
  // 声明函数: index
  const index = toasts.value.findIndex(t => t.id === id)
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (index > -1) {
    toasts.value.splice(index, 1)
  }
}

// 定义 success 方法
function success(message, duration) {
  // 返回处理结果
  return show({ type: 'success', message, duration })
}

// 定义 error 方法
function error(message, duration) {
  // 返回处理结果
  return show({ type: 'error', message, duration })
}

// 定义 warning 方法
function warning(message, duration) {
  // 返回处理结果
  return show({ type: 'warning', message, duration })
}

// 定义 info 方法
function info(message, duration) {
  // 返回处理结果
  return show({ type: 'info', message, duration })
}

// 定义 getIcon 方法
function getIcon(type) {
  // 声明变量: icons
  const icons = {
    success: 'M20 6L9 17l-5-5',
    error: 'M18 6L6 18M6 6l12 12',
    warning: 'M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z',
    info: 'M12 16v-4M12 8h.01',
  }
  // 返回处理结果
  return icons[type] || icons.info
}

defineExpose({ show, success, error, warning, info, remove })
</script>

<template>
  <Teleport to="body"> <div class="base-toast-container">
      <TransitionGroup name="toast-slide">
        <div v-for="toast in toasts" :key="toast.id" class="base-toast" :class="`toast-${toast.type}`">
          <svg class="toast-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"> <path :d="getIcon(toast.type)" />
          </svg>
          <span class="toast-message">{{ toast.message }}</span>
          <button class="toast-close" @click="remove(toast.id)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.base-toast-container {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 12px;
  pointer-events: none;
}

.base-toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  min-width: 280px;
  max-width: 420px;
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border-subtle, #e8e3d9);
  border-radius: var(--radius-md, 10px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  pointer-events: all;
}

.toast-icon {
  flex-shrink: 0;
}

.toast-success {
  border-left: 3px solid var(--color-success, #2d7d4a);
}

.toast-success .toast-icon {
  color: var(--color-success, #2d7d4a);
}

.toast-error {
  border-left: 3px solid var(--color-error, #b23a2a);
}

.toast-error .toast-icon {
  color: var(--color-error, #b23a2a);
}

.toast-warning {
  border-left: 3px solid var(--color-warning, #b8791e);
}

.toast-warning .toast-icon {
  color: var(--color-warning, #b8791e);
}

.toast-info {
  border-left: 3px solid var(--color-accent-copper, #8b6f47);
}

.toast-info .toast-icon {
  color: var(--color-accent-copper, #8b6f47);
}

.toast-message {
  flex: 1;
  font-size: 14px;
  color: var(--color-text-primary, #1d1d1f);
}

.toast-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  color: var(--color-text-tertiary, #aeaeb2);
  background: none;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.toast-close:hover {
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-secondary, #faf8f4);
}

.toast-slide-enter-active {
  transition: all 0.25s var(--ease-out);
}

.toast-slide-leave-active {
  transition: all 0.2s var(--ease-in);
}

.toast-slide-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.toast-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
