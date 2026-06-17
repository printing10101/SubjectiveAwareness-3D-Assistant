<!--
 ============================================================================
 BaseModal.vue - BaseModal UI 组件
 ============================================================================

 @file BaseModal.vue
 @description 帮信罪主观明知智能分析系统 - BaseModal UI 组件
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
 * BaseModal — 通用模态框组件
 *
 * 支持标题、确认/取消按钮、关闭按钮
 * 可访问性：Esc 键关闭、role=dialog、aria-modal、焦点管理
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

// 导入外部依赖模块
import BaseButton from './BaseButton.vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseModal' })

// 声明变量: props
const props = defineProps({
  /** 是否显示 */
  visible: { type: Boolean, default: false },
  /** 标题 */
  title: { type: String, default: '' },
  /** 确认按钮文字 */
  confirmText: { type: String, default: '确认' },
  /** 取消按钮文字 */
  cancelText: { type: String, default: '取消' },
  /** 确认按钮变体 */
  confirmVariant: { type: String, default: 'primary' },
  /** 确认按钮加载状态 */
  confirmLoading: { type: Boolean, default: false },
  /** 是否显示关闭按钮 */
  showClose: { type: Boolean, default: true },
  /** 是否显示取消按钮 */
  showCancel: { type: Boolean, default: true },
  /** 宽度 */
  width: { type: String, default: '500px' },
  /** 是否按 Esc 关闭 */
  closeOnEsc: { type: Boolean, default: true },
})

// 声明变量: emit
const emit = defineEmits(['update:visible', 'confirm', 'cancel', 'close'])

// 计算属性：基于响应式数据自动计算并缓存结果
const isVisible = computed({
  get: () => props.visible,
  // 向父组件触发自定义事件
  set: (val) => emit('update:visible', val),
})

// 定义 onConfirm 方法
function onConfirm() {
  // 向父组件触发自定义事件
  emit('confirm')
}

// 定义 onCancel 方法
function onCancel() {
  // 向父组件触发自定义事件
  emit('cancel')
  isVisible.value = false
}

// 定义 onClose 方法
function onClose() {
  // 向父组件触发自定义事件
  emit('close')
  isVisible.value = false
}

// 定义 onOverlayClick 方法
function onOverlayClick(e) {
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (e.target === e.currentTarget) {
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

// 焦点陷阱：打开时聚焦模态框，关闭时恢复焦点
let previousActiveElement = null

// 数据监听器：监听响应式数据变化并执行副作用
watch(isVisible, async (val) => {
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (val) {
    previousActiveElement = document.activeElement
    await nextTick()
    // 声明变量: modal
    const modal = document.querySelector('.base-modal')
    // 条件分支：根据状态执行不同的业务逻辑

    // 条件判断：根据条件执行不同逻辑
    if (modal) {
      // 声明变量: focusable
      const focusable = modal.querySelector(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      // 条件分支：根据状态执行不同的业务逻辑

      // 条件判断：根据条件执行不同逻辑
      if (focusable) {
        focusable.focus()
      // 条件不满足时的备选逻辑
      } else {
        modal.focus()
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
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="isVisible" class="base-modal-overlay" @click="onOverlayClick">
        <div class="base-modal" :style="{ width }" role="dialog" aria-modal="true" :aria-labelledby="title ? 'modal-title' : undefined" tabindex="-1">
          <div v-if="title || showClose" class="modal-header">
            <h3 v-if="title" id="modal-title" class="modal-title">{{ title }}</h3>
            <button v-if="showClose" class="modal-close" :aria-label="'关闭对话框'" @click="onClose">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <slot></slot>
          </div>

          <div class="modal-footer">
            <slot name="footer">
              <BaseButton v-if="showCancel" variant="secondary" @click="onCancel">{{ cancelText }}</BaseButton>
              <BaseButton :variant="confirmVariant" :loading="confirmLoading" @click="onConfirm">{{ confirmText }}</BaseButton>
            </slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.base-modal-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 1000;
  padding: 24px;
}

.base-modal {
  background: var(--color-bg-card, #fff);
  border-radius: var(--radius-md, 10px);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

.modal-fade-enter-active {
  transition: opacity 0.25s var(--ease-out);
}

.modal-fade-enter-active .base-modal {
  transition: transform 0.25s var(--ease-out), opacity 0.25s var(--ease-out);
}

.modal-fade-leave-active {
  transition: opacity 0.2s var(--ease-in);
}

.modal-fade-leave-active .base-modal {
  transition: transform 0.2s var(--ease-in), opacity 0.2s var(--ease-in);
}

.modal-fade-enter-from {
  opacity: 0;
}

.modal-fade-enter-from .base-modal {
  opacity: 0;
  transform: scale(0.95);
}

.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-leave-to .base-modal {
  opacity: 0;
  transform: scale(0.95);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-subtle, #e8e3d9);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary, #1d1d1f);
  margin: 0;
}

.modal-close {
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

.modal-close:hover {
  color: var(--color-text-primary, #1d1d1f);
  background: var(--color-bg-secondary, #faf8f4);
}

.modal-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-subtle, #e8e3d9);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s var(--ease-out);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
