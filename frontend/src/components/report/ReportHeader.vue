<script setup>
// 接收 props
defineProps({
  isDownloadingPdf: {
    type: Boolean,
    default: false,
  },
  isDownloadingDocx: {
    type: Boolean,
    default: false,
  },
})

// 发射事件
const emit = defineEmits(['download-pdf', 'download-docx', 'go-back'])

function handleDownloadPdf() {
  emit('download-pdf')
}

function handleDownloadDocx() {
  emit('download-docx')
}

function handleGoBack() {
  emit('go-back')
}
</script>

<template>
  <div class="report-header">
    <div class="header-left">
      <h1 class="report-title">帮信罪辅助裁定分析报告</h1>
      <span class="report-version">V1.1.0</span>
    </div>
    <div class="header-actions">
      <button
        class="btn btn-primary"
        :disabled="isDownloadingPdf"
        @click="handleDownloadPdf"
      >
        <span v-if="isDownloadingPdf">下载中...</span>
        <span v-else>📕 下载 PDF</span>
      </button>
      <button
        class="btn btn-secondary"
        :disabled="isDownloadingDocx"
        @click="handleDownloadDocx"
      >
        <span v-if="isDownloadingDocx">下载中...</span>
        <span v-else>📘 下载 DOCX</span>
      </button>
      <button
        class="btn btn-outline"
        @click="handleGoBack"
      >
        ← 返回
      </button>
    </div>
  </div>
</template>

<style scoped>
.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  background: white;
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.report-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.report-version {
  padding: 0.25rem 0.5rem;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: var(--border-radius);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #4338ca;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--border-color);
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.btn-outline:hover {
  background: var(--bg-tertiary);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .report-header {
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
  }

  .header-actions {
    width: 100%;
    justify-content: center;
  }
}
</style>
