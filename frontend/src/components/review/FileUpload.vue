<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { nextTick } from 'vue'

const props = defineProps({
  allowedTypes: { type: Array, default: () => ['.pdf', '.docx', '.doc'] },
  maxFileSize: { type: Number, default: 20 * 1024 * 1024 },
})

const emit = defineEmits(['uploaded', 'clear'])

const isDragOver = ref(false)
const uploadProgress = ref(0)
const isUploading = ref(false)
const uploadError = ref('')
const uploadedFile = ref(null)

const extractProgress = ref(0)
const isExtracting = ref(false)
const extractError = ref('')

const fileSizeLabel = computed(() => {
  if (!uploadedFile.value) return ''
  const size = uploadedFile.value.size
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(2)} MB`
})

function handleDragOver(e) {
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = true
}

function handleDragLeave(e) {
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = false
}

function handleDrop(e) {
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) validateAndUpload(files[0])
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length > 0) validateAndUpload(files[0])
  e.target.value = ''
}

function validateAndUpload(file) {
  uploadError.value = ''
  extractError.value = ''
  const ext = `.${file.name.split('.').pop().toLowerCase()}`
  if (!props.allowedTypes.includes(ext)) {
    uploadError.value = `不支持的文件格式: ${ext}。支持的格式: ${props.allowedTypes.join(', ')}`
    return
  }
  if (file.size > props.maxFileSize) {
    uploadError.value = `文件大小超过限制 (最大 20MB)`
    return
  }
  uploadedFile.value = file
  uploadDocument(file)
}

async function uploadDocument(file) {
  isUploading.value = true
  uploadProgress.value = 0
  const formData = new FormData()
  formData.append('file', file)
  try {
    const response = await axios.post('/api/extract', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        }
      },
    })
    uploadProgress.value = 100
    isUploading.value = false
    isExtracting.value = true
    extractProgress.value = 50
    setTimeout(() => {
      extractProgress.value = 100
      isExtracting.value = false
      emit('uploaded', { text: response.data.text, file: uploadedFile.value })
    }, 300)
  } catch (error) {
    isUploading.value = false
    isExtracting.value = false
    uploadError.value = error.message || '文档上传失败，请重试'
    uploadedFile.value = null
  }
}

function handleRemoveFile() {
  uploadedFile.value = null
  uploadProgress.value = 0
}

function reset() {
  uploadedFile.value = null
  uploadProgress.value = 0
  isUploading.value = false
  uploadError.value = ''
  extractProgress.value = 0
  isExtracting.value = false
  extractError.value = ''
}

defineExpose({ reset, uploadedFile, uploadError, extractError })
</script>

<template>
  <div class="upload-section card">
    <h3 class="section-title">文档上传</h3>
    <div
      class="drop-zone"
      :class="{ 'drag-over': isDragOver, 'has-file': uploadedFile }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      @click="!uploadedFile && $refs.fileInput?.click()"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.docx,.doc"
        class="file-input-hidden"
        @change="handleFileSelect"
      />
      <template v-if="!uploadedFile && !isUploading">
        <div class="drop-icon">📄</div>
        <p class="drop-text">拖放文件到此处，或点击上传</p>
        <p class="drop-hint">支持 PDF、DOCX、DOC 格式，最大 20MB</p>
      </template>
      <template v-else-if="isUploading">
        <div class="upload-progress">
          <div class="upload-spinner"></div>
          <p class="upload-status">正在上传... {{ uploadProgress }}%</p>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
        </div>
      </template>
      <template v-else-if="uploadedFile && !isExtracting && !isUploading">
        <div class="file-info">
          <span class="file-icon">📄</span>
          <div class="file-details">
            <span class="file-name">{{ uploadedFile.name }}</span>
            <span class="file-size">{{ fileSizeLabel }}</span>
          </div>
          <button class="file-remove" @click.stop="handleRemoveFile">×</button>
        </div>
      </template>
      <template v-else-if="isExtracting">
        <div class="upload-progress">
          <div class="upload-spinner"></div>
          <p class="upload-status">正在提取文本... {{ extractProgress }}%</p>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: extractProgress + '%' }"></div>
          </div>
        </div>
      </template>
    </div>
    <div v-if="uploadedFile && !isUploading && !isExtracting" class="upload-actions">
      <button class="btn btn-secondary btn-sm" @click="handleRemoveFile">重新选择</button>
    </div>
  </div>
</template>

<style scoped>
.upload-section { padding: 1.5rem; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.75rem; }
.drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--border-radius-lg);
  padding: 2.5rem 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  background: var(--bg-secondary);
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.drop-zone:hover { border-color: var(--color-primary); background: rgba(79, 70, 229, 0.03); }
.drop-zone.drag-over { border-color: var(--color-primary); background: rgba(79, 70, 229, 0.08); transform: scale(1.01); }
.drop-zone.has-file { border-style: solid; border-color: var(--color-success); background: #f0fdf4; cursor: default; padding: 1.25rem 1.5rem; min-height: auto; }
.file-input-hidden { display: none; }
.drop-icon { font-size: 3rem; margin-bottom: 0.75rem; }
.drop-text { font-size: 1rem; font-weight: 500; color: var(--text-primary); margin-bottom: 0.5rem; }
.drop-hint { font-size: 0.8rem; color: var(--text-tertiary); }
.upload-progress { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; }
.upload-spinner { width: 32px; height: 32px; border: 3px solid var(--bg-tertiary); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.upload-status { font-size: 0.9rem; color: var(--text-secondary); font-weight: 500; }
.progress-bar { width: 100%; max-width: 240px; height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, var(--color-primary), #7c3aed); border-radius: 3px; transition: width 0.3s ease; }
.file-info { display: flex; align-items: center; gap: 0.75rem; width: 100%; }
.file-icon { font-size: 1.5rem; flex-shrink: 0; }
.file-details { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 0.125rem; min-width: 0; }
.file-name { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
.file-size { font-size: 0.75rem; color: var(--text-tertiary); }
.file-remove { background: none; border: none; font-size: 1.5rem; color: var(--text-tertiary); cursor: pointer; padding: 0 0.25rem; line-height: 1; transition: color var(--transition-fast); }
.file-remove:hover { color: var(--color-danger); }
.upload-actions { margin-top: 0.75rem; display: flex; gap: 0.5rem; }
</style>
