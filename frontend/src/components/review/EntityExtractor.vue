<script setup>
import axios from 'axios'

const props = defineProps({
  editorContent: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['extracted', 'error'])

const isExtracting = ref(false)
const extractError = ref('')

async function handleExtract() {
  if (!props.editorContent.trim() || props.disabled) return
  isExtracting.value = true
  extractError.value = ''
  try {
    const response = await axios.post('/api/extract_entities', { text: props.editorContent })
    emit('extracted', response.data)
  } catch (error) {
    extractError.value = error.message || '实体抽取失败，请重试'
    emit('error', extractError.value)
  } finally {
    isExtracting.value = false
  }
}

function resetError() {
  extractError.value = ''
}

defineExpose({ isExtracting, extractError, resetError })
</script>

<template>
  <div class="extract-section card">
    <h3 class="section-title">信息抽取</h3>
    <p class="section-desc">从案件事实文本中自动抽取实体和关系信息</p>
    <button
      class="btn btn-primary btn-extract"
      :disabled="!editorContent.trim() || isExtracting || disabled"
      @click="handleExtract"
    >
      <span v-if="isExtracting" class="btn-loading">
        <span class="loading-spinner-small"></span>
        抽取中...
      </span>
      <span v-else>开始抽取</span>
    </button>
  </div>
</template>

<style scoped>
.extract-section { padding: 1.5rem; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.75rem; }
.section-desc { font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1rem; }
.btn-extract { width: 100%; }
.btn-loading { display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
.loading-spinner-small { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255, 255, 255, 0.3); border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
