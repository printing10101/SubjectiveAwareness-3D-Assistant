<script setup>
defineOptions({ name: 'CaseCard' })

const props = defineProps({
  caseData: {
    type: Object,
    required: true,
  },
  status: {
    type: String,
    default: 'pending',
  },
})

const emit = defineEmits(['click', 'delete', 'view'])

const statusConfig = {
  pending: { label: '待分析', class: 'status-pending' },
  analyzing: { label: '分析中', class: 'status-analyzing' },
  completed: { label: '已完成', class: 'status-completed' },
  failed: { label: '失败', class: 'status-failed' },
}

const currentStatus = statusConfig[props.status] || statusConfig.pending

function handleClick() {
  emit('click', props.caseData)
}

function handleView() {
  emit('view', props.caseData)
}

function handleDelete() {
  emit('delete', props.caseData)
}

function getTruncatedText(text, maxLength = 120) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength).trimEnd()  }...`
}
</script>

<template>
  <div
    class="case-card"
    @click="handleClick"
  >
    <div class="case-card-header">
      <h3 class="case-card-title">{{ caseData.name || caseData.title || '未命名案件' }}</h3>
      <span
        class="case-card-status"
        :class="currentStatus.class"
      >
        {{ currentStatus.label }}
      </span>
    </div>

    <p class="case-card-description">
      {{ getTruncatedText(caseData.fact_text || caseData.description || caseData.summary) }}
    </p>

    <div class="case-card-footer">
      <span
        v-if="caseData.created_at"
        class="case-card-date"
      >
        {{ new Date(caseData.created_at).toLocaleDateString('zh-CN') }}
      </span>
      <div class="case-card-actions">
        <button
          class="case-card-btn"
          @click.stop="handleView"
        >
          查看
        </button>
        <button
          class="case-card-btn case-card-btn-danger"
          @click.stop="handleDelete"
        >
          删除
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.case-card {
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: var(--border-radius-lg, 12px);
  padding: 1.25rem;
  cursor: pointer;
  transition: all var(--transition-fast, 150ms ease);
}

.case-card:hover {
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
  border-color: var(--color-primary, #4f46e5);
}

.case-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.case-card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0;
  line-height: 1.4;
}

.case-card-status {
  flex-shrink: 0;
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
}

.status-pending {
  color: #92400e;
  background: rgba(234, 179, 8, 0.12);
}

.status-analyzing {
  color: #1e40af;
  background: rgba(59, 130, 246, 0.12);
}

.status-completed {
  color: #166534;
  background: rgba(34, 197, 94, 0.12);
}

.status-failed {
  color: #991b1b;
  background: rgba(239, 68, 68, 0.12);
}

.case-card-description {
  font-size: 0.875rem;
  color: var(--text-secondary, #64748b);
  margin: 0 0 1rem;
  line-height: 1.6;
}

.case-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.case-card-date {
  font-size: 0.75rem;
  color: var(--text-tertiary, #94a3b8);
}

.case-card-actions {
  display: flex;
  gap: 0.5rem;
}

.case-card-btn {
  font-size: 0.8125rem;
  font-weight: 500;
  font-family: inherit;
  padding: 0.375rem 0.75rem;
  border: none;
  border-radius: var(--border-radius, 8px);
  cursor: pointer;
  transition: all var(--transition-fast, 150ms ease);
  color: var(--color-primary, #4f46e5);
  background: rgba(79, 70, 229, 0.08);
}

.case-card-btn:hover {
  background: rgba(79, 70, 229, 0.15);
}

.case-card-btn-danger {
  color: var(--color-danger, #ef4444);
  background: rgba(239, 68, 68, 0.08);
}

.case-card-btn-danger:hover {
  background: rgba(239, 68, 68, 0.15);
}
</style>