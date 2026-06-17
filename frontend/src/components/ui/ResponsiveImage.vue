<!--
 ============================================================================
 ResponsiveImage.vue - ResponsiveImage UI 组件
 ============================================================================

 @file ResponsiveImage.vue
 @description 帮信罪主观明知智能分析系统 - ResponsiveImage UI 组件
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
<script setup>
// ============================================================================
// 组件脚本模块 - Script Setup
// ============================================================================
// 使用 Vue 3 Composition API 的 <script setup> 语法糖
// 包含：响应式数据定义、计算属性、方法函数、生命周期钩子
// ============================================================================

/**
 * ResponsiveImage — 响应式图片组件
 * 
 * 支持 WebP/JPG 格式切换、响应式尺寸和懒加载优化
 * 性能优化：
 * - 自动使用 WebP 格式（体积更小）
 * - 支持懒加载（减少首屏加载）
 * - 提供 srcset 和 sizes（适配不同设备）
 * - 设置宽高属性（避免布局偏移 CLS）
 */
defineOptions({ name: 'ResponsiveImage' })

/**
 * @typedef {Object} Props
 * @property {string} name - 图片名称（不含扩展名）
 * @property {string} srcPath - 图片目录路径
 * @property {string} [alt=''] - alt 文本
 * @property {string} [className=''] - 自定义类名
 * @property {boolean} [lazy=true] - 是否懒加载
 * @property {number} [width=1000] - 图片宽度（用于 CLS 优化）
 * @property {number} [height=600] - 图片高度（用于 CLS 优化）
 */

// 声明变量: props
const props = defineProps({
  name: {
    type: String,
    required: true,
  },
  srcPath: {
    type: String,
    required: true,
  },
  alt: {
    type: String,
    default: '',
  },
  className: {
    type: String,
    default: '',
  },
  lazy: {
    type: Boolean,
    default: true,
  },
  width: {
    type: Number,
    default: 1000,
  },
  height: {
    type: Number,
    default: 600,
  },
})

// 构建图片路径
const basePath = `${props.srcPath}/${props.name}`
// 声明变量: webpPath
const webpPath = `${basePath}.webp`
// 声明变量: webpMobilePath
const webpMobilePath = `${basePath}-mobile.webp`
// 声明变量: jpgPath
const jpgPath = `${basePath}.jpg`
// 声明变量: jpgMobilePath
const jpgMobilePath = `${basePath}-mobile.jpg`
</script>

<template>
  <picture :class="['responsive-image', className]">
    <source :srcset="`${webpMobilePath} 500w, ${webpPath} 1000w`" sizes="(max-width: 768px) 500px, 1000px" type="image/webp" />
    <source :srcset="`${jpgMobilePath} 500w, ${jpgPath} 1000w`" sizes="(max-width: 768px) 500px, 1000px" type="image/jpeg" />
    <img :src="jpgPath" :alt="alt" :loading="lazy ? 'lazy' : 'eager'" :width="width" :height="height" decoding="async" class="responsive-image__img" @load="$event.target.classList.add('loaded')" />
  </picture>
</template>

<style scoped>
.responsive-image {
  display: block;
  width: 100%;
  height: auto;
  /* 防止布局偏移 */
  aspect-ratio: v-bind('props.width / props.height');
}

.responsive-image__img {
  display: block;
  width: 100%;
  height: auto;
  object-fit: cover;
  /* 懒加载淡入效果 */
  opacity: 0;
  transition: opacity 0.3s ease;
}

.responsive-image__img.loaded {
  opacity: 1;
}

/* 非懒加载图片直接显示 */
.responsive-image__img:not([loading="lazy"]) {
  opacity: 1;
}
</style>
