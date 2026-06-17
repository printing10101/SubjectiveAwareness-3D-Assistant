<!--
 ============================================================================
 AnimatedProgress.vue - AnimatedProgress UI 组件
 ============================================================================

 @file AnimatedProgress.vue
 @description 帮信罪主观明知智能分析系统 - AnimatedProgress UI 组件
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
 * AnimatedProgress — 进度条动画组件
 * 
 * 实现宽度从 0% 到目标百分比的平滑过渡
 * 持续时间：400ms，缓动函数：ease-out
 * 支持动态更新进度值
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { ref, watch, computed } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'AnimatedProgress' })

// 声明变量: props
const props = defineProps({
  /** 进度值（0-100） */
  value: {
    type: Number,
    default: 0,
    validator: (v) => v >= 0 && v <= 100,
  },
  /** 动画持续时间（毫秒） */
  duration: {
    type: Number,
    default: 400,
  },
  /** 是否显示百分比文字 */
  showLabel: {
    type: Boolean,
    default: true,
  },
  /** 进度条高度 */
  height: {
    type: String,
    default: '8px',
  },
  /** 进度条颜色 */
  color: {
    type: String,
    default: 'var(--color-primary, #4f46e5)',
  },
  /** 背景颜色 */
  bgColor: {
    type: String,
    default: 'var(--color-bg-secondary, #f0f0f0)',
  },
  /** 是否圆角 */
  rounded: {
    type: Boolean,
    default: true,
  },
})

// 响应式数据：使用 ref 创建可响应的基础类型数据
const displayValue = ref(0)
// 计算属性：基于响应式数据自动计算并缓存结果
const progressWidth = computed(() => `${displayValue.value}%`)

// 监听值变化
// 数据监听器：监听响应式数据变化并执行副作用
watch(() => props.value, (newValue) => {
  // 使用 CSS transition 实现平滑过渡
  displayValue.value = newValue
}, { immediate: true })
</script>

<template>
  <div class="animated-progress">
    <div class="progress-track" :style="{ height, background: bgColor, borderRadius: rounded ? '999px' : '0', }">
      <div class="progress-fill" :style="{ width: progressWidth, background: color, borderRadius: rounded ? '999px' : '0', transition: `width ${duration}ms var(--ease-out)`, }"></div>
    </div>
    <div v-if="showLabel" class="progress-label">
      {{ Math.round(displayValue) }}%
    </div>
  </div>
</template>

<style scoped>
.animated-progress {
  width: 100%;
}

.progress-track {
  width: 100%;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  min-width: 0;
  will-change: width;
}

.progress-label {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1d1d1f);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
