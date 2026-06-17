<script setup>
// ============================================================================
// 组件脚本模块 - Script Setup
// ============================================================================
// 使用 Vue 3 Composition API 的 <script setup> 语法糖
// 包含：响应式数据定义、计算属性、方法函数、生命周期钩子
// ============================================================================

// =====================================================================
// 组件逻辑模块 - 包含数据定义、计算属性、方法和生命周期钩子
// =====================================================================

// 导入依赖模块：引入组件、工具函数和状态管理
// ----------------------------------------------------------------------------
// 依赖导入区域：引入组件、工具函数、状态管理、API 接口等
// ----------------------------------------------------------------------------
import { computed } from 'vue'

// ----------------------------------------------------------------------------
const props = defineProps({
  pathType: {
    type: String,
    required: true,
    validator: (value) => ['direct-evidence', 'objective-anomaly', 'behavior-pattern', 'supplementary'].includes(value)
  },
  label: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  }
})

const pathConfig = {
  'direct-evidence': {
    color: '#22c55e',
    bgColor: 'rgba(34, 197, 94, 0.1)',
    icon: '✓',
    label: '直接证据路径'
  },
  'objective-anomaly': {
    color: '#f97316',
    bgColor: 'rgba(249, 115, 22, 0.1)',
    icon: '⚠',
    label: '客观异常路径'
  },
  'behavior-pattern': {
    color: '#ef4444',
    bgColor: 'rgba(239, 68, 68, 0.1)',
    icon: '⚡',
    label: '行为模式路径'
  },
  'supplementary': {
    color: '#64748b',
    bgColor: 'rgba(100, 116, 139, 0.1)',
    icon: '📋',
    label: '补充审查路径'
  }
}

// 计算属性：基于响应式数据自动计算并缓存结果
const config = computed(() => pathConfig[props.pathType])

// 计算属性：基于响应式数据自动计算并缓存结果
const badgeStyle = computed(() => ({
  color: config.value.color,
  backgroundColor: config.value.bgColor,
  borderColor: config.value.color
}))
</script>

<template>
  <div class="standard-path-badge" :style="badgeStyle">
    <span class="badge-icon">{{ config.icon }}</span>
    <div class="badge-content">
      <div class="badge-label">{{ label }}</div>
      <div v-if="description" class="badge-description">{{ description }}</div>
    </div>
    <span class="badge-type">{{ config.label }}</span>
  </div>
</template>

<style scoped>
.standard-path-badge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border: 1px solid;
  border-radius: 8px;
  font-size: 0.875rem;
  transition: all var(--transition-fast, 150ms ease);
}

.standard-path-badge:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.badge-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.badge-content {
  flex: 1;
  min-width: 0;
}

.badge-label {
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 0.125rem;
}

.badge-description {
  font-size: 0.8125rem;
  opacity: 0.85;
  line-height: 1.4;
}

.badge-type {
  font-size: 0.75rem;
  font-weight: 500;
  opacity: 0.75;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .standard-path-badge {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .badge-type {
    width: 100%;
    text-align: right;
    margin-top: 0.25rem;
  }
}
</style>
