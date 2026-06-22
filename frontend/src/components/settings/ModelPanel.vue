<script setup>
import { ref, onMounted } from 'vue'

import axios from 'axios'

const props = defineProps({
  errorMsg: {
    type: Object,
    default: () => ({ value: null }),
  },
})

const modelInfo = ref(null)
const isModelLoading = ref(false)

async function fetchModelVersion() {
  isModelLoading.value = true
  try {
    const res = await axios.get('/api/model-version')
    modelInfo.value = res.data
  } catch {
    modelInfo.value = null
  } finally {
    isModelLoading.value = false
  }
}

onMounted(() => {
  fetchModelVersion()
})

defineExpose({
  fetchModelVersion,
  modelInfo,
  isModelLoading,
})
</script>

<template>
  <div class="model-panel">
    <div class="panel-header">
      <h3 class="panel-title">模型版本信息</h3>
      <button class="btn btn-ghost btn-sm" @click="fetchModelVersion" :disabled="isModelLoading">
        <span class="btn-icon">🔄</span>
        刷新
      </button>
    </div>

    <div v-if="isModelLoading" class="loading-state">加载中...</div>

    <div v-else-if="modelInfo" class="model-info">
      <div class="info-card card">
        <div class="info-row">
          <span class="info-label">模型名称：</span>
          <span class="info-value">{{ modelInfo.model_name || '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">版本号：</span>
          <span class="info-value version-tag">{{ modelInfo.version || '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">提供商：</span>
          <span class="info-value">{{ modelInfo.provider || '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">端点地址：</span>
          <span class="info-value mono">{{ modelInfo.endpoint || '—' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">状态：</span>
          <span class="info-value">
            <span class="status-badge" :class="modelInfo.status === 'online' ? 'status-online' : 'status-offline'">
              {{ modelInfo.status === 'online' ? '在线' : '离线' }}
            </span>
          </span>
        </div>
        <div v-if="modelInfo.description" class="info-row">
          <span class="info-label">描述：</span>
          <span class="info-value">{{ modelInfo.description }}</span>
        </div>
        <div v-if="modelInfo.updated_at" class="info-row">
          <span class="info-label">更新时间：</span>
          <span class="info-value">{{ modelInfo.updated_at }}</span>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>暂无模型信息</p>
    </div>
  </div>
</template>

<style scoped>
.model-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: var(--text-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.loading-state,
.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-tertiary);
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.info-card {
  padding: var(--space-4);
}

.info-row {
  display: flex;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-secondary);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  flex-shrink: 0;
  width: 120px;
  font-size: var(--text-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

.info-value {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.info-value.mono {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.version-tag {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
}

.status-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-weight-medium);
}

.status-online {
  background: var(--color-success-light);
  color: var(--color-success);
}

.status-offline {
  background: var(--color-danger-light);
  color: var(--color-danger);
}
</style>
