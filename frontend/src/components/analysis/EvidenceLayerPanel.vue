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
import { ref, computed } from 'vue'

// ----------------------------------------------------------------------------
const props = defineProps({
  evidenceLayers: {
    type: Object,
    default: () => ({})
  }
})

// 响应式数据：使用 ref 创建可响应的基础类型数据
const activeTab = ref('layer1')

const layerConfig = [
  { id: 'layer1', label: '第一层：直接证据', icon: '📋' },
  { id: 'layer2', label: '第二层：客观证据', icon: '📊' },
  { id: 'layer3', label: '第三层：行为证据', icon: '🎭' },
  { id: 'layer4', label: '第四层：补充证据', icon: '📎' }
]

// 方法函数 getLayerCount：封装组件交互逻辑和业务流程
const getLayerCount = (layerId) => {
  const layer = props.evidenceLayers[layerId]
  if (!layer || !Array.isArray(layer.items)) return 0
  return layer.items.length
}

// 计算属性：基于响应式数据自动计算并缓存结果
const hasEvidence = computed(() => {
  return layerConfig.some(layer => getLayerCount(layer.id) > 0)
})

// 计算属性：基于响应式数据自动计算并缓存结果
const currentLayer = computed(() => {
  return props.evidenceLayers[activeTab.value] || {}
})
</script>

<template>
  <div v-if="hasEvidence" class="evidence-layer-panel">
    <div class="panel-header">
      <h3 class="panel-title">证据分层展示</h3>
    </div>
    
    <div class="tabs-container">
      <div class="tabs-header">
        <button v-for="layer in layerConfig" :key="layer.id" class="tab-button" :class="{ active: activeTab === layer.id }" @click="activeTab = layer.id">
          <span class="tab-icon">{{ layer.icon }}</span>
          <span class="tab-label">{{ layer.label }}</span>
          <span v-if="getLayerCount(layer.id)> 0" class="tab-badge">
            {{ getLayerCount(layer.id) }}
          </span>
        </button>
      </div>
      
      <div class="tab-content">
        <div v-if="!currentLayer.items || currentLayer.items.length === 0" class="empty-state">
          <p>暂无证据</p>
        </div>
        
        <div v-else class="evidence-list">
          <div v-for="(item, index) in currentLayer.items" :key="index" class="evidence-item">
            <div class="evidence-header">
              <span class="evidence-index">{{ index + 1 }}</span>
              <span v-if="item.type" class="evidence-type">{{ item.type }}</span>
            </div>
            
            <div v-if="item.title" class="evidence-title">
              {{ item.title }}
            </div>
            
            <div v-if="item.content" class="evidence-content">
              {{ item.content }}
            </div>
            
            <div v-if="item.source" class="evidence-source">
              <span class="source-label">来源:</span>
              <span class="source-value">{{ item.source }}</span>
            </div>
            
            <div v-if="item.relevance" class="evidence-relevance">
              <span class="relevance-label">关联性:</span>
              <span class="relevance-value">{{ item.relevance }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.evidence-layer-panel {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
}

.panel-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--border-color, #e2e8f0);
}

.panel-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0;
}

.tabs-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tabs-header {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid var(--border-color, #e2e8f0);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast, 150ms ease);
  white-space: nowrap;
  font-size: 0.875rem;
  color: var(--text-secondary, #64748b);
  font-weight: 500;
}

.tab-button:hover {
  color: var(--text-primary, #1e293b);
  background: var(--bg-secondary, #f8fafc);
}

.tab-button.active {
  color: var(--color-accent-copper, #8B6F47);
  border-bottom-color: var(--color-accent-copper, #8B6F47);
}

.tab-icon {
  font-size: 1rem;
}

.tab-label {
  flex: 1;
}

.tab-badge {
  padding: 0.25rem 0.5rem;
  background: rgba(139, 111, 71, 0.1);
  color: var(--color-accent-copper, #8B6F47);
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  min-width: 20px;
  text-align: center;
}

.tab-content {
  min-height: 200px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--text-tertiary, #94a3b8);
  font-size: 0.9375rem;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.evidence-item {
  padding: 1rem;
  background: var(--bg-secondary, #f8fafc);
  border-radius: var(--border-radius, 8px);
  border-left: 3px solid var(--color-accent-copper, #8B6F47);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.evidence-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.evidence-index {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-accent-copper, #8B6F47);
  color: white;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

.evidence-type {
  padding: 0.25rem 0.625rem;
  background: var(--bg-tertiary, #f1f5f9);
  border-radius: 12px;
  font-size: 0.75rem;
  color: var(--text-secondary, #64748b);
  font-weight: 500;
}

.evidence-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  line-height: 1.4;
}

.evidence-content {
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--text-primary, #1e293b);
}

.evidence-source,
.evidence-relevance {
  display: flex;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.source-label,
.relevance-label {
  color: var(--text-secondary, #64748b);
  font-weight: 500;
}

.source-value,
.relevance-value {
  color: var(--text-primary, #1e293b);
}

@media (max-width: 768px) {
  .evidence-layer-panel {
    padding: 1rem;
  }

  .panel-title {
    font-size: 1rem;
  }

  .tabs-header {
    gap: 0.25rem;
  }

  .tab-button {
    padding: 0.625rem 0.75rem;
    font-size: 0.8125rem;
  }

  .tab-label {
    display: none;
  }

  .tab-icon {
    font-size: 1.125rem;
  }
}

@media (max-width: 640px) {
  .evidence-item {
    padding: 0.75rem;
  }

  .evidence-title {
    font-size: 0.9375rem;
  }

  .evidence-content {
    font-size: 0.875rem;
  }
}
</style>
