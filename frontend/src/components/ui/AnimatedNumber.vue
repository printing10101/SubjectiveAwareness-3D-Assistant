<!--
 ============================================================================
 AnimatedNumber.vue - AnimatedNumber UI 组件
 ============================================================================

 @file AnimatedNumber.vue
 @description 帮信罪主观明知智能分析系统 - AnimatedNumber UI 组件
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
 * AnimatedNumber — 数字滚动动画组件
 * 
 * 实现数值从初始值到目标值的平滑累加动画
 * 持续时间：600ms，采用 ease-out 缓动函数
 * 支持整数和带小数点数值（最多两位小数）
 */
// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { ref, watch, onMounted, onUnmounted } from 'vue'

// ----------------------------------------------------------------------------
defineOptions({ name: 'AnimatedNumber' })

// 声明变量: props
const props = defineProps({
  /** 目标值 */
  value: {
    type: Number,
    default: 0,
  },
  /** 初始值 */
  initialValue: {
    type: Number,
    default: 0,
  },
  /** 动画持续时间（毫秒） */
  duration: {
    type: Number,
    default: 600,
  },
  /** 小数位数（0-2） */
  decimals: {
    type: Number,
    default: 0,
    validator: (v) => v >= 0 && v <= 2,
  },
  /** 前缀 */
  prefix: {
    type: String,
    default: '',
  },
  /** 后缀 */
  suffix: {
    type: String,
    default: '',
  },
  /** 是否自动播放 */
  autoplay: {
    type: Boolean,
    default: true,
  },
})

// 响应式数据：使用 ref 创建可响应的基础类型数据
const displayValue = ref(props.initialValue)
// 声明变量: animationFrameId
let animationFrameId = null
// 声明变量: startTime
let startTime = null

// ease-out 缓动函数
// 定义 easeOut 方法
function easeOut(t) {
  // 返回处理结果
  return 1 - Math.pow(1 - t, 3)
}

// 格式化数字显示
// 定义 formatNumber 方法
function formatNumber(num) {
  // 声明变量: fixed
  const fixed = num.toFixed(props.decimals)
  // 返回处理结果
  return props.prefix + fixed + props.suffix
}

// 动画函数
// 定义 animate 方法
function animate(timestamp) {
  // 条件判断：根据条件执行不同逻辑
  if (!startTime) startTime = timestamp
  
  // 声明变量: elapsed
  const elapsed = timestamp - startTime
  // 声明变量: progress
  const progress = Math.min(elapsed / props.duration, 1)
  // 声明变量: easedProgress
  const easedProgress = easeOut(progress)
  
  // 声明变量: startValue
  const startValue = props.initialValue
  // 声明变量: endValue
  const endValue = props.value
  // 声明变量: currentValue
  const currentValue = startValue + (endValue - startValue) * easedProgress
  
  displayValue.value = currentValue
  
  // 条件分支：根据状态执行不同的业务逻辑

  
  // 条件判断：根据条件执行不同逻辑
  if (progress < 1) {
    animationFrameId = requestAnimationFrame(animate)
  }
}

// 开始动画
// 定义 startAnimation 方法
function startAnimation() {
  // 取消之前的动画
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  
  startTime = null
  displayValue.value = props.initialValue
  animationFrameId = requestAnimationFrame(animate)
}

// 监听值变化
// 数据监听器：监听响应式数据变化并执行副作用
watch(() => props.value, () => {
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (props.autoplay) {
    startAnimation()
  }
})

// 生命周期钩子：组件挂载完成后执行初始化逻辑
// 生命周期钩子：onMounted
onMounted(() => {
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (props.autoplay) {
    startAnimation()
  }
})

// 生命周期钩子：组件卸载前执行清理逻辑
// 生命周期钩子：onUnmounted
onUnmounted(() => {
  // 条件分支：根据状态执行不同的业务逻辑

  // 条件判断：根据条件执行不同逻辑
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
})

// 暴露方法
defineExpose({ startAnimation })
</script>

<template>
  <span class="animated-number">
    {{ formatNumber(displayValue) }}
  </span>
</template>

<style scoped>
.animated-number {
  display: inline-block;
  font-variant-numeric: tabular-nums;
}
</style>
