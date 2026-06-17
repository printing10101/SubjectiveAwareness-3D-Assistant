<!--
 ============================================================================
 BaseDrawer.vue - BaseDrawer UI 组件
 ============================================================================

 @file BaseDrawer.vue
 @description 帮信罪主观明知智能分析系统 - BaseDrawer UI 组件
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
 * BaseDrawer — 抽屉组件
 *
 * 支持从左/右/上/下滑入，带背景遮罩
 * 可访问性：Esc 键关闭、role=dialog、aria-modal、焦点管理
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseDrawer' })

// 声明变量: props
const props = defineProps({
  /** 是否显示 */
  visible: { type: Boolean, default: false },
  /** 标题 */
  title: { type: String, default: '' },
  /** 方向: left | right | top | bottom */
  direction: {
    type: String,
    default: 'right',
    validator: (v) => ['left', 'right', 'top', 'bottom'].includes(v),
  },
  /** 宽度（left/right方向） */
  width: { type: String, default: '300px' },
  /** 高度（top/bottom方向） */
  height: { type: String, default: '300px' },
  /** 是否显示关闭按钮 */
  showClose: { type: Boolean, default: true },
  /** 是否显示背景遮罩 */
  showOverlay: { type: Boolean, default: true },
  /** 点击遮罩是否关闭 */
  closeOnClickOverlay: { type: Boolean, default: true },
  /** 是否按 Esc 关闭 */
  closeOnEsc: { type: Boolean, default: true },
})

// 声明变量: emit
const emit = defineEmits(['update:visible', 'close'])

// 计算属性：基于响应式数据自动计算并缓存结果
const isVisible = computed({
  get: () => props.visible,
  // 向父组件触发自定义事件
  set: (val) => emit('update:visible', val),
})

// 定义 onClose 方法
function onClose() {
  // 向父组件触发自定义事件
  emit('close')
  isVisible.value = false
}

// 定义 onOverlayClick 方法
function onOverlayClick() {
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (props.closeOnClickOverlay) {
    onClose()
  }
}

// Esc 键关闭
// 定义 handleKeydown 方法
function handleKeydown(e) {
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (e.key === 'Escape' && props.closeOnEsc && isVisible.value) {
    e.preventDefault()
    onClose()
  }
}

// 焦点陷阱：打开时聚焦抽屉，关闭时恢复焦点
let previousActiveElement = null

// 数据监听器：监听响应式数据变化并执行副作用
watch(isVisible, async (val) => {
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (val) {
    previousActiveElement = document.activeElement
    await nextTick()
    // 声明变量: drawer
    const drawer = document.querySelector('.base-drawer')
    // 条件分支：根据状态执行不同的业务逻辑

    // 条件判断：根据条件执行不同逻辑
    if (drawer) {
      // 声明变量: focusable
      const focusable = drawer.querySelector(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      // 条件分支：根据状态执行不同的业务逻辑

      // 条件判断：根据条件执行不同逻辑
      if (focusable) {
        focusable.focus()
      // 条件不满足时的备选逻辑
      } else {
        drawer.focus()
      }
    }
  } else // 条件分支：根据状态执行不同的业务逻辑
 if (previousActiveElement) {
    previousActiveElement.focus()
    previousActiveElement = null
  }
})

// 生命周期钩子：组件挂载完成后执行初始化逻辑
// 生命周期钩子：onMounted
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Teleport to="body"> <Transition :name="`drawer-${direction}`">
      <div v-if="isVisible" class="base-drawer-overlay" :class="{ 'has-overlay': showOverlay }" @click="onOverlayClick">
        <div class="base-drawer" :class="[`drawer-${direction}`]" :style="{ width: direction === 'left' || direction === 'right' ? width : '100%', height: direction === 'top' || direction === 'bottom' ? height : '100%', }" role="dialog" aria-modal="true" :aria-labelledby="title ? 'drawer-title' : undefined" tabindex="-1" @click.stop>
          <div v-if="title || showClose" class="drawer-header">
            <h3 v-if="title" id="drawer-title" class="drawer-title">{{ title }}</h3>
            <button v-if="showClose" class="drawer-close" :aria-label="'关闭抽屉'" @click="onClose">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="drawer-body">
            <slot></slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.base-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  pointer-events: none;
}

.base-drawer-overlay.has-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  pointer-events: all;
}

.base-drawer {
  position: absolute;
  background: var(--color-bg-card, #fff);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  pointer-events: all;
}

.drawer-left {
  left: 0;
  top: 0;
  bottom: 0;
}

.drawer-right {
  right: 0;
  top: 0;
  bottom: 0;
}

.drawer-top {
  top: 0;
  left: 0;
  right: 0;
}

.drawer-bottom {
  bottom: 0;
  left: 0;
  right: 0;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-subtle, #e8e3d9);
}

.drawer-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary, #1d1d1f);
  margin: 0;
}

.drawer-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  color: var(--color-text-tertiary, #aeaeb2);
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.drawer-close:hover {
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-secondary, #faf8f4);
}

.drawer-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

/* 左侧抽屉动画 */
.drawer-left-enter-active,
.drawer-left-leave-active {
  transition: transform 0.3s var(--ease-out);
}

.drawer-left-enter-from,
.drawer-left-leave-to {
  transform: translateX(-100%);
}

/* 右侧抽屉动画 */
.drawer-right-enter-active,
.drawer-right-leave-active {
  transition: transform 0.3s var(--ease-out);
}

.drawer-right-enter-from,
.drawer-right-leave-to {
  transform: translateX(100%);
}

/* 顶部抽屉动画 */
.drawer-top-enter-active,
.drawer-top-leave-active {
  transition: transform 0.3s var(--ease-out);
}

.drawer-top-enter-from,
.drawer-top-leave-to {
  transform: translateY(-100%);
}

/* 底部抽屉动画 */
.drawer-bottom-enter-active,
.drawer-bottom-leave-active {
  transition: transform 0.3s var(--ease-out);
}

.drawer-bottom-enter-from,
.drawer-bottom-leave-to {
  transform: translateY(100%);
}

/* 遮罩层淡入淡出 */
.base-drawer-overlay {
  transition: opacity 0.3s var(--ease-out);
}

.drawer-left-enter-active ~ .base-drawer-overlay,
.drawer-left-leave-active ~ .base-drawer-overlay,
.drawer-right-enter-active ~ .base-drawer-overlay,
.drawer-right-leave-active ~ .base-drawer-overlay,
.drawer-top-enter-active ~ .base-drawer-overlay,
.drawer-top-leave-active ~ .base-drawer-overlay,
.drawer-bottom-enter-active ~ .base-drawer-overlay,
.drawer-bottom-leave-active ~ .base-drawer-overlay {
  opacity: 0;
}
</style>
