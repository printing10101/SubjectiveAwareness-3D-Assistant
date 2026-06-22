<script setup>
import { computed } from 'vue'

const props = defineProps({
  editorContent: { type: String, default: '' },
  isAnalyzing: { type: Boolean, default: false },
})

const emit = defineEmits(['analyze'])

const canAnalyze = computed(() => props.editorContent.trim().length > 10 && !props.isAnalyzing)
</script>

<template>
  <button class="analyze-btn" :disabled="!canAnalyze" @click="emit('analyze')">
    <span v-if="isAnalyzing" class="analyze-btn-loading">
      <span class="loading-spinner-small"></span>
      分析中...
    </span>
    <span v-else>开始分析 →</span>
  </button>
</template>

<style scoped>
.analyze-btn {
  width: 100%;
  padding: 1.125rem 2rem;
  font-size: 1.125rem;
  font-weight: 600;
  border: none;
  border-radius: var(--border-radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: white;
  box-shadow: var(--shadow-lg);
  font-family: inherit;
}
.analyze-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 14px 20px -3px rgba(79, 70, 229, 0.3); }
.analyze-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.analyze-btn-loading { display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
.loading-spinner-small { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255, 255, 255, 0.3); border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
