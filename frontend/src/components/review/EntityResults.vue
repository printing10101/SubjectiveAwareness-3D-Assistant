<script setup>
import { computed } from 'vue'

const props = defineProps({
  extractionResult: { type: Object, default: null },
})

const emit = defineEmits(['update-entity', 'remove-entity', 'add-entity'])

const hasEntities = computed(() => {
  return props.extractionResult &&
    props.extractionResult.entities &&
    Object.keys(props.extractionResult.entities).length > 0
})

const entityKeys = computed(() => {
  if (!props.extractionResult || !props.extractionResult.entities) return []
  return Object.keys(props.extractionResult.entities)
})

function formatConfidence(val) {
  return `${(val * 100).toFixed(1)}%`
}

function getConfidenceColor(val) {
  if (val >= 0.8) return 'confidence-high'
  if (val >= 0.5) return 'confidence-mid'
  return 'confidence-low'
}

function handleUpdateEntity(category, index, field, value) {
  emit('update-entity', { category, index, field, value })
}

function handleRemoveEntity(category, index) {
  emit('remove-entity', { category, index })
}
</script>

<template>
  <div v-if="hasEntities" class="result-section card">
    <div class="result-header">
      <h3 class="section-title">抽取结果</h3>
      <span class="result-count">
        {{ extractionResult.entity_count }} 实体 / {{ extractionResult.relation_count }} 关系
      </span>
    </div>

    <div class="entity-categories">
      <div v-for="category in entityKeys" :key="category" class="entity-category">
        <h4 class="category-title">{{ category }}</h4>
        <div class="entity-list">
          <div
            v-for="(entity, index) in extractionResult.entities[category]"
            :key="category + '-' + index"
            class="entity-card"
          >
            <div class="entity-header">
              <span class="entity-type">{{ entity.type }}</span>
              <span class="entity-confidence" :class="getConfidenceColor(entity.confidence)">
                {{ formatConfidence(entity.confidence) }}
              </span>
            </div>
            <div class="entity-body">
              <input
                class="entity-value-input"
                :value="entity.value"
                placeholder="实体值"
                @input="handleUpdateEntity(category, index, 'value', $event.target.value)"
              />
            </div>
            <button class="entity-remove" title="删除此实体" @click="handleRemoveEntity(category, index)">×</button>
          </div>
        </div>
      </div>
    </div>

    <div class="entity-actions">
      <button class="btn btn-secondary btn-sm" @click="emit('add-entity')">+ 添加实体</button>
    </div>

    <!-- 关系列表 -->
    <div v-if="extractionResult.relations.length > 0" class="relations-section">
      <h4 class="category-title">实体关系</h4>
      <div class="relations-list">
        <div v-for="(rel, index) in extractionResult.relations" :key="'rel-' + index" class="relation-card">
          <span class="relation-from">{{ rel.from }}</span>
          <span class="relation-arrow">→</span>
          <span class="relation-type">{{ rel.type }}</span>
          <span class="relation-arrow">→</span>
          <span class="relation-to">{{ rel.to }}</span>
          <span v-if="rel.amount" class="relation-amount">({{ rel.amount }}元)</span>
          <span class="relation-conf" :class="getConfidenceColor(rel.confidence || 0.5)">
            {{ formatConfidence(rel.confidence || 0.5) }}
          </span>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="placeholder-card card">
    <div class="placeholder-icon">🔍</div>
    <h3 class="placeholder-title">尚未进行信息抽取</h3>
    <p class="placeholder-desc">上传文档后点击"开始抽取"<br/>自动识别案件关键实体</p>
  </div>
</template>

<style scoped>
.result-section { padding: 1.5rem; }
.result-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.75rem; }
.result-count { font-size: 0.8rem; color: var(--text-tertiary); font-weight: 500; }
.entity-categories { display: flex; flex-direction: column; gap: 1rem; max-height: 400px; overflow-y: auto; }
.entity-category { padding: 0.75rem; background: var(--bg-secondary); border-radius: var(--border-radius); }
.category-title { font-size: 0.85rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; padding-bottom: 0.375rem; border-bottom: 1px solid var(--border-color); }
.entity-list { display: flex; flex-direction: column; gap: 0.5rem; }
.entity-card { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.625rem; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; transition: all var(--transition-fast); position: relative; }
.entity-card:hover { border-color: var(--color-primary); box-shadow: var(--shadow-sm); }
.entity-header { display: flex; align-items: center; gap: 0.375rem; flex-shrink: 0; }
.entity-type { font-size: 0.7rem; font-weight: 600; color: var(--color-primary); background: rgba(79, 70, 229, 0.08); padding: 0.125rem 0.375rem; border-radius: 3px; white-space: nowrap; }
.entity-confidence { font-size: 0.65rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 3px; white-space: nowrap; }
.confidence-high { color: #166534; background: #dcfce7; }
.confidence-mid { color: #92400e; background: #fef3c7; }
.confidence-low { color: #991b1b; background: #fef2f2; }
.entity-body { flex: 1; min-width: 0; }
.entity-value-input { width: 100%; padding: 0.25rem 0.375rem; font-size: 0.85rem; font-family: inherit; color: var(--text-primary); background: transparent; border: 1px solid transparent; border-radius: 3px; outline: none; transition: all var(--transition-fast); }
.entity-value-input:hover { border-color: var(--border-color); }
.entity-value-input:focus { border-color: var(--color-primary); background: white; }
.entity-remove { background: none; border: none; font-size: 1rem; color: var(--text-tertiary); cursor: pointer; padding: 0 0.125rem; line-height: 1; transition: color var(--transition-fast); flex-shrink: 0; }
.entity-remove:hover { color: var(--color-danger); }
.entity-actions { margin-top: 0.75rem; display: flex; gap: 0.5rem; }
.relations-section { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color); }
.relations-list { display: flex; flex-direction: column; gap: 0.5rem; max-height: 200px; overflow-y: auto; }
.relation-card { display: flex; align-items: center; gap: 0.375rem; padding: 0.5rem 0.75rem; background: var(--bg-secondary); border-radius: 6px; font-size: 0.85rem; flex-wrap: wrap; }
.relation-from, .relation-to { font-weight: 600; color: var(--text-primary); }
.relation-arrow { color: var(--text-tertiary); font-size: 0.75rem; }
.relation-type { color: var(--color-primary); font-weight: 500; background: rgba(79, 70, 229, 0.06); padding: 0.125rem 0.375rem; border-radius: 3px; }
.relation-amount { color: var(--text-secondary); font-size: 0.8rem; }
.relation-conf { font-size: 0.65rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 3px; margin-left: auto; }
.placeholder-card { padding: 2rem; text-align: center; }
.placeholder-icon { font-size: 3rem; margin-bottom: 0.75rem; }
.placeholder-title { font-size: 1.125rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; }
.placeholder-desc { font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6; }
@media (max-width: 768px) { .entity-card { flex-wrap: wrap; } .relation-card { font-size: 0.8rem; } }
</style>
