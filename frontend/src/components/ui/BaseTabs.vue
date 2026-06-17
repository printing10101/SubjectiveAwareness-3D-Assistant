<!--
 ============================================================================
 BaseTabs.vue - BaseTabs UI 组件
 ============================================================================

 @file BaseTabs.vue
 @description 帮信罪主观明知智能分析系统 - BaseTabs UI 组件
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
 * BaseTabs — 通用标签页组件
 *
 * 支持多个标签切换
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { ref, watch } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'BaseTabs' })

// 声明变量: props
const props = defineProps({
  /** 当前激活的标签 */
  modelValue: { type: [String, Number], default: '' },
  /** 标签列表 [{ key, label, disabled }] */
  tabs: { type: Array, default: () => [] },
})

// 声明变量: emit
const emit = defineEmits(['update:modelValue', 'change'])

// 响应式数据：使用 ref 创建可响应的基础类型数据
const activeTab = ref(props.modelValue || (props.tabs[0] && props.tabs[0].key))

// 数据监听器：监听响应式数据变化并执行副作用
watch(() => props.modelValue, (val) => {
  // 条件判断：根据条件执行不同逻辑
  if (val) activeTab.value = val
})

// 定义 selectTab 方法
function selectTab(tab) {
  // 条件判断：根据条件执行不同逻辑
  if (tab.disabled) return
  activeTab.value = tab.key
  // 向父组件触发自定义事件
  emit('update:modelValue', tab.key)
  // 向父组件触发自定义事件
  emit('change', tab.key)
}
</script>

<template>
  <div class="base-tabs">
    <div class="tabs-header">
      <button v-for="tab in tabs" :key="tab.key" class="tab-item" :class="{ active: activeTab === tab.key, disabled: tab.disabled }" @click="selectTab(tab)">
        {{ tab.label }}
      </button>
    </div>

    <div class="tabs-content">
      <slot :name="activeTab" :active-tab="activeTab"></slot>
    </div>
  </div>
</template>

<style scoped>
.base-tabs {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.tabs-header {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--color-border-subtle, #e8e3d9);
  margin-bottom: 20px;
}

.tab-item {
  padding: 10px 16px;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary, #6e6e73);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
  margin-bottom: -1px;
}

.tab-item:hover:not(.disabled) {
  color: var(--color-text-primary, #1d1d1f);
}

.tab-item.active {
  color: var(--color-accent-copper, #8b6f47);
  border-bottom-color: var(--color-accent-copper, #8b6f47);
}

.tab-item.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.tabs-content {
  flex: 1;
}
</style>
