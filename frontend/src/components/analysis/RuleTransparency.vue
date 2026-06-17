<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  analysisResult: {
    type: Object,
    default: null,
  },
})

// 响应式数据
const searchQuery = ref('')
const sortBy = ref('weight') // 'weight' | 'relevance'
const activeTab = ref('triggered') // 'triggered' | 'conflicts' | 'untriggered' | 'tags'

// 计算属性 - 命中的规则
const triggeredRules = computed(() => {
  if (!props.analysisResult?.triggered_rules) return []
  let rules = [...props.analysisResult.triggered_rules]

  // 搜索过滤
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    rules = rules.filter(
      (rule) =>
        rule.name?.toLowerCase().includes(query) ||
        rule.description?.toLowerCase().includes(query) ||
        rule.legal_article?.toLowerCase().includes(query)
    )
  }

  // 排序
  if (sortBy.value === 'weight') {
    rules.sort((a, b) => (b.weight || 0) - (a.weight || 0))
  }

  return rules
})

// 计算属性 - 规则冲突
const ruleConflicts = computed(() => {
  if (!props.analysisResult?.rule_conflicts) return []
  return props.analysisResult.rule_conflicts
})

// 计算属性 - 未触发的规则
const untriggeredRules = computed(() => {
  if (!props.analysisResult?.untriggered_rules) return []
  return props.analysisResult.untriggered_rules
})

// 计算属性 - 命中的标签
const factTags = computed(() => {
  if (!props.analysisResult?.fact_tags) return []
  return props.analysisResult.fact_tags
})

// 方法
function getWeightColor(weight) {
  if (weight >= 0.8) return '#ef4444'
  if (weight >= 0.5) return '#f59e0b'
  return '#94a3b8'
}

function getTagSize(importance) {
  if (importance >= 0.8) return 'tag-large'
  if (importance >= 0.5) return 'tag-medium'
  return 'tag-small'
}

function getTagColor(importance) {
  if (importance >= 0.8) return '#ef4444'
  if (importance >= 0.5) return '#f59e0b'
  return '#6366f1'
}
</script>

<template>
  <div class="rule-transparency">
    <div class="panel-header">
      <h3 class="panel-title">规则透明度面板</h3>
      <div class="panel-actions">
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          placeholder="搜索规则..."
        >
        <select
          v-model="sortBy"
          class="sort-select"
        >
          <option value="weight">按权重排序</option>
          <option value="relevance">按相关性排序</option>
        </select>
      </div>
    </div>

    <div class="tab-nav">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'triggered' }"
        @click="activeTab = 'triggered'"
      >
        命中规则 ({{ triggeredRules.length }})
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'tags' }"
        @click="activeTab = 'tags'"
      >
        事实标签 ({{ factTags.length }})
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'conflicts' }"
        @click="activeTab = 'conflicts'"
      >
        规则冲突 ({{ ruleConflicts.length }})
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'untriggered' }"
        @click="activeTab = 'untriggered'"
      >
        未触发规则 ({{ untriggeredRules.length }})
      </button>
    </div>

    <div class="tab-content">
      <!-- 命中规则 -->
      <div
        v-if="activeTab === 'triggered'"
        class="rules-list"
      >
        <div
          v-for="(rule, index) in triggeredRules"
          :key="index"
          class="rule-card"
        >
          <div class="rule-header">
            <span class="rule-name">{{ rule.name }}</span>
            <span
              class="rule-weight"
              :style="{ background: getWeightColor(rule.weight) }"
            >
              权重: {{ (rule.weight * 100).toFixed(0) }}%
            </span>
          </div>
          <p class="rule-description">
            {{ rule.description }}
          </p>
          <div class="rule-meta">
            <div
              v-if="rule.conditions"
              class="meta-item"
            >
              <span class="meta-label">适用条件:</span>
              <span class="meta-value">{{ rule.conditions }}</span>
            </div>
            <div
              v-if="rule.legal_article"
              class="meta-item"
            >
              <span class="meta-label">引用法条:</span>
              <span class="meta-value legal">{{ rule.legal_article }}</span>
            </div>
          </div>
        </div>
        <div
          v-if="triggeredRules.length === 0"
          class="empty-state"
        >
          暂无命中的规则
        </div>
      </div>

      <!-- 事实标签 -->
      <div
        v-if="activeTab === 'tags'"
        class="tags-cloud"
      >
        <span
          v-for="(tag, index) in factTags"
          :key="index"
          class="tag-item"
          :class="getTagSize(tag.importance)"
          :style="{ borderColor: getTagColor(tag.importance) }"
        >
          {{ tag.name }}
          <span class="tag-importance">{{ (tag.importance * 100).toFixed(0) }}%</span>
        </span>
        <div
          v-if="factTags.length === 0"
          class="empty-state"
        >
          暂无事实标签
        </div>
      </div>

      <!-- 规则冲突 -->
      <div
        v-if="activeTab === 'conflicts'"
        class="conflicts-list"
      >
        <div
          v-for="(conflict, index) in ruleConflicts"
          :key="index"
          class="conflict-card"
        >
          <div class="conflict-header">
            <span class="conflict-icon">⚡</span>
            <span class="conflict-title">{{ conflict.rule_a }} ↔ {{ conflict.rule_b }}</span>
          </div>
          <p class="conflict-description">
            {{ conflict.description }}
          </p>
          <div class="conflict-meta">
            <div class="meta-item">
              <span class="meta-label">冲突点:</span>
              <span class="meta-value">{{ conflict.conflict_point }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">解决方式:</span>
              <span class="meta-value resolution">{{ conflict.resolution }}</span>
            </div>
          </div>
        </div>
        <div
          v-if="ruleConflicts.length === 0"
          class="empty-state"
        >
          暂无规则冲突
        </div>
      </div>

      <!-- 未触发规则 -->
      <div
        v-if="activeTab === 'untriggered'"
        class="untriggered-list"
      >
        <div
          v-for="(rule, index) in untriggeredRules"
          :key="index"
          class="untriggered-card"
        >
          <div class="untriggered-header">
            <span class="rule-name">{{ rule.name }}</span>
            <span class="status-badge">未触发</span>
          </div>
          <p class="rule-description">
            {{ rule.description }}
          </p>
          <div class="untriggered-reason">
            <span class="reason-label">未触发原因:</span>
            <span class="reason-value">{{ rule.reason }}</span>
          </div>
        </div>
        <div
          v-if="untriggeredRules.length === 0"
          class="empty-state"
        >
          暂无未触发规则
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rule-transparency {
  background: white;
  border-radius: var(--border-radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.panel-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.panel-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.search-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 0.875rem;
  width: 200px;
  transition: border-color var(--transition-fast);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.sort-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 0.875rem;
  background: white;
  cursor: pointer;
}

.tab-nav {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 1.5rem;
  overflow-x: auto;
}

.tab-btn {
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.tab-content {
  min-height: 300px;
}

.rules-list,
.conflicts-list,
.untriggered-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.rule-card,
.conflict-card,
.untriggered-card {
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
  border-left: 3px solid var(--color-primary);
}

.rule-header,
.conflict-header,
.untriggered-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.rule-name {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.9375rem;
}

.rule-weight {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  color: white;
}

.rule-description {
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 0.75rem;
}

.rule-meta,
.conflict-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.meta-label {
  color: var(--text-tertiary);
  min-width: 80px;
}

.meta-value {
  color: var(--text-primary);
}

.meta-value.legal {
  color: var(--color-primary);
  font-weight: 500;
}

.meta-value.resolution {
  color: #16a34a;
  font-weight: 500;
}

.tags-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 1rem 0;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  background: white;
  border: 2px solid;
  border-radius: 20px;
  font-weight: 500;
  transition: transform var(--transition-fast);
}

.tag-item:hover {
  transform: scale(1.05);
}

.tag-large {
  font-size: 1rem;
  padding: 0.625rem 1rem;
}

.tag-medium {
  font-size: 0.875rem;
}

.tag-small {
  font-size: 0.75rem;
  padding: 0.375rem 0.625rem;
}

.tag-importance {
  font-size: 0.6875rem;
  opacity: 0.7;
}

.conflict-icon {
  font-size: 1.25rem;
}

.conflict-title {
  font-weight: 600;
  color: var(--text-primary);
}

.status-badge {
  padding: 0.25rem 0.5rem;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.untriggered-reason {
  display: flex;
  gap: 0.5rem;
  font-size: 0.8125rem;
  padding: 0.75rem;
  background: rgba(239, 68, 68, 0.05);
  border-radius: var(--border-radius);
  margin-top: 0.75rem;
}

.reason-label {
  color: var(--text-tertiary);
  min-width: 100px;
}

.reason-value {
  color: var(--text-primary);
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--text-tertiary);
  font-size: 0.9375rem;
}

@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .panel-actions {
    width: 100%;
    flex-direction: column;
  }

  .search-input,
  .sort-select {
    width: 100%;
  }

  .tab-nav {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .meta-item {
    flex-direction: column;
    gap: 0.25rem;
  }

  .meta-label {
    min-width: auto;
  }
}
</style>
