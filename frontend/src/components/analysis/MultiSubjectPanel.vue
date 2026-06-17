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
  subjects: {
    type: Array,
    default: () => []
  }
})

// 响应式数据：使用 ref 创建可响应的基础类型数据
const expandedSubjects = ref(new Set())

function toggleSubject(subjectId) {
  if (expandedSubjects.value.has(subjectId)) {
    expandedSubjects.value.delete(subjectId)
  } else {
    expandedSubjects.value.add(subjectId)
  }
}

function isExpanded(subjectId) {
  return expandedSubjects.value.has(subjectId)
}

// 计算属性：基于响应式数据自动计算并缓存结果
const hasSubjects = computed(() => props.subjects && props.subjects.length > 0)
</script>

<template>
  <div v-if="hasSubjects" class="multi-subject-panel">
    <div class="panel-header">
      <h3 class="panel-title">涉案主体列表</h3>
      <span class="subject-count">{{ subjects.length }} 人</span>
    </div>
    
    <div class="subject-list">
      <div v-for="subject in subjects" :key="subject.id" class="subject-card" :class="{ expanded: isExpanded(subject.id) }">
        <div class="card-header" @click="toggleSubject(subject.id)">
          <div class="subject-info">
            <div class="subject-name">{{ subject.name }}</div>
            <div v-if="subject.role" class="subject-role">{{ subject.role }}</div>
          </div>
          <div class="expand-icon" :class="{ rotated: isExpanded(subject.id) }">
            ▼
          </div>
        </div>
        
        <div v-if="isExpanded(subject.id)" class="card-content">
          <div v-if="subject.description" class="subject-description">
            {{ subject.description }}
          </div>
          
          <div v-if="subject.evidence" class="subject-evidence">
            <div class="evidence-label">关联证据:</div>
            <div class="evidence-text">{{ subject.evidence }}</div>
          </div>
          
          <div v-if="subject.analysis" class="subject-analysis">
            <div class="analysis-label">分析说明:</div>
            <div class="analysis-text">{{ subject.analysis }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.multi-subject-panel {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.subject-count {
  padding: 0.375rem 0.75rem;
  background: rgba(139, 111, 71, 0.1);
  color: var(--color-accent-copper, #8B6F47);
  border-radius: 16px;
  font-size: 0.875rem;
  font-weight: 600;
}

.subject-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.subject-card {
  background: var(--bg-secondary, #f8fafc);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: var(--border-radius, 8px);
  overflow: hidden;
  transition: all var(--transition-fast, 150ms ease);
}

.subject-card:hover {
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
}

.subject-card.expanded {
  border-color: var(--color-accent-copper, #8B6F47);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  cursor: pointer;
  transition: background var(--transition-fast, 150ms ease);
}

.card-header:hover {
  background: var(--bg-tertiary, #f1f5f9);
}

.subject-info {
  flex: 1;
  min-width: 0;
}

.subject-name {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin-bottom: 0.25rem;
}

.subject-role {
  font-size: 0.875rem;
  color: var(--text-secondary, #64748b);
}

.expand-icon {
  font-size: 0.75rem;
  color: var(--text-tertiary, #94a3b8);
  transition: transform var(--transition-fast, 150ms ease);
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

.card-content {
  padding: 0 1rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 500px;
  }
}

.subject-description {
  padding: 0.75rem;
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius, 8px);
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--text-primary, #1e293b);
}

.subject-evidence,
.subject-analysis {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.evidence-label,
.analysis-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary, #64748b);
}

.evidence-text,
.analysis-text {
  padding: 0.75rem;
  background: var(--bg-primary, #fff);
  border-left: 3px solid var(--color-accent-copper, #8B6F47);
  border-radius: var(--border-radius, 8px);
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--text-primary, #1e293b);
}

@media (max-width: 768px) {
  .multi-subject-panel {
    padding: 1rem;
  }

  .panel-title {
    font-size: 1rem;
  }

  .subject-name {
    font-size: 0.9375rem;
  }
}

@media (max-width: 640px) {
  .card-header {
    padding: 0.75rem;
  }

  .card-content {
    padding: 0 0.75rem 0.75rem;
  }
}
</style>
