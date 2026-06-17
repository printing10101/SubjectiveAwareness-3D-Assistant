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
  alerts: {
    type: Array,
    default: () => []
  },
  dismissible: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['dismiss'])

// 计算属性：基于响应式数据自动计算并缓存结果
const hasAlerts = computed(() => props.alerts && props.alerts.length > 0)

function handleDismiss(index) {
  emit('dismiss', index)
}

const alertTypeConfig = {
  warning: {
    icon: '⚠️',
    bgColor: 'rgba(251, 191, 36, 0.1)',
    borderColor: '#f59e0b',
    textColor: '#92400e'
  },
  error: {
    icon: '❌',
    bgColor: 'rgba(239, 68, 68, 0.1)',
    borderColor: '#ef4444',
    textColor: '#991b1b'
  },
  info: {
    icon: 'ℹ️',
    bgColor: 'rgba(59, 130, 246, 0.1)',
    borderColor: '#3b82f6',
    textColor: '#1e40af'
  }
}

function getAlertStyle(type) {
  const config = alertTypeConfig[type] || alertTypeConfig.warning
  return {
    backgroundColor: config.bgColor,
    borderColor: config.borderColor,
    color: config.textColor
  }
}
</script>

<template>
  <div v-if="hasAlerts" class="boundary-alert-banner">
    <div v-for="(alert, index) in alerts" :key="index" class="alert-item" :style="getAlertStyle(alert.type)">
      <div class="alert-content">
        <span class="alert-icon">{{ alertTypeConfig[alert.type]?.icon || '⚠️' }}</span>
        <div class="alert-text">
          <div v-if="alert.title" class="alert-title">{{ alert.title }}</div>
          <div v-if="alert.message" class="alert-message">{{ alert.message }}</div>
        </div>
      </div>
      <button v-if="dismissible" class="dismiss-button" @click="handleDismiss(index)" aria-label="关闭警告">
        ✕
      </button>
    </div>
  </div>
</template>

<style scoped>
.boundary-alert-banner {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.alert-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border: 2px solid;
  border-radius: var(--border-radius, 8px);
  transition: all var(--transition-fast, 150ms ease);
}

.alert-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.alert-content {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  flex: 1;
}

.alert-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
  line-height: 1;
}

.alert-text {
  flex: 1;
  min-width: 0;
}

.alert-title {
  font-size: 0.9375rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
  line-height: 1.4;
}

.alert-message {
  font-size: 0.875rem;
  line-height: 1.5;
  opacity: 0.9;
}

.dismiss-button {
  background: transparent;
  border: none;
  font-size: 1.125rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all var(--transition-fast, 150ms ease);
  opacity: 0.6;
  flex-shrink: 0;
}

.dismiss-button:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.05);
}

.dismiss-button:active {
  transform: scale(0.95);
}

@media (max-width: 768px) {
  .boundary-alert-banner {
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .alert-item {
    padding: 0.875rem 1rem;
  }

  .alert-icon {
    font-size: 1.125rem;
  }

  .alert-title {
    font-size: 0.875rem;
  }

  .alert-message {
    font-size: 0.8125rem;
  }
}

@media (max-width: 640px) {
  .alert-item {
    padding: 0.75rem;
    gap: 0.5rem;
  }

  .alert-content {
    gap: 0.5rem;
  }

  .dismiss-button {
    padding: 0.375rem;
    font-size: 1rem;
  }
}
</style>
