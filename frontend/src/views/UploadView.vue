<script setup>
import { ref, computed } from 'vue'

import axios from 'axios'
import { useRouter } from 'vue-router'

import { useAnalysisStore } from '../stores/analysisStore.js'

const router = useRouter()
const analysisStore = useAnalysisStore()

// 响应式数据
const isDragging = ref(false)
const uploadProgress = ref(0)
const isUploading = ref(false)
const uploadError = ref(null)
const uploadedFile = ref(null)
const parsedData = ref(null)
const isEditing = ref(false)
const editableData = ref({})

// 计算属性
const hasFile = computed(() => !!uploadedFile.value)
const hasParsedData = computed(() => !!parsedData.value)
const canSave = computed(() => hasParsedData.value && isEditing.value)

// 支持的文件格式
const allowedFormats = ['.doc', '.pdf', '.txt']
const allowedMimeTypes = [
  'application/msword',
  'application/pdf',
  'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

// 方法
function handleDragOver(event) {
  event.preventDefault()
  isDragging.value = true
}

function handleDragLeave(event) {
  event.preventDefault()
  isDragging.value = false
}

function handleDrop(event) {
  event.preventDefault()
  isDragging.value = false

  const files = event.dataTransfer.files
  if (files.length > 0) {
    handleFileSelect(files[0])
  }
}

function handleFileInput(event) {
  const files = event.target.files
  if (files.length > 0) {
    handleFileSelect(files[0])
  }
}

function handleFileSelect(file) {
  // 验证文件格式
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowedFormats.includes(fileExtension)) {
    uploadError.value = `不支持的文件格式，仅支持 ${allowedFormats.join(', ')} 格式`
    return
  }

  // 验证MIME类型
  if (!allowedMimeTypes.includes(file.type) && file.type !== '') {
    uploadError.value = '文件类型不正确'
    return
  }

  uploadedFile.value = file
  uploadError.value = null
  handleUploadFile()
}

async function handleUploadFile() {
  if (!uploadedFile.value) return

  isUploading.value = true
  uploadProgress.value = 0
  uploadError.value = null

  const formData = new FormData()
  formData.append('file', uploadedFile.value)

  try {
    const response = await axios.post('/api/cases/extract', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        uploadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      },
    })

    parsedData.value = response.data
    editableData.value = { ...response.data }
    isEditing.value = true
  } catch (err) {
    uploadError.value = err.response?.data?.detail || err.message || '文件上传失败，请稍后重试'
  } finally {
    isUploading.value = false
  }
}

function handleSaveEditedData() {
  parsedData.value = { ...editableData.value }
  isEditing.value = false
  analysisStore.setAnalysisResult(parsedData.value)
  router.push('/analysis')
}

function handleClearFile() {
  uploadedFile.value = null
  parsedData.value = null
  editableData.value = {}
  uploadProgress.value = 0
  uploadError.value = null
  isEditing.value = false
}

function handleBackToHome() {
  router.push('/')
}
</script>

<template>
  <div class="upload-page">
    <div class="container">
      <div class="page-header">
        <button
          class="back-btn"
          @click="handleBackToHome"
        >
          &larr; 返回首页
        </button>
        <h1 class="page-title">上传案件文件</h1>
        <p class="page-subtitle">支持 .doc、.pdf、.txt 格式文件上传与解析</p>
      </div>

      <div class="upload-layout">
        <!-- 上传区域 -->
        <div
          v-if="!hasFile"
          class="upload-section"
        >
          <div
            class="drop-zone"
            :class="{ dragging: isDragging }"
            @dragover="handleDragOver"
            @dragleave="handleDragLeave"
            @drop="handleDrop"
          >
            <div class="drop-zone-content">
              <div class="upload-icon">📁</div>
              <p class="drop-text">拖放文件到此处上传</p>
              <p class="drop-hint">或</p>
              <label class="file-select-btn">
                <input
                  type="file"
                  accept=".doc,.pdf,.txt"
                  class="file-input"
                  @change="handleFileInput"
                >
                选择文件
              </label>
              <p class="format-hint">支持格式: {{ allowedFormats.join(', ') }}</p>
            </div>
          </div>

          <div
            v-if="uploadError"
            class="error-alert"
          >
            <span class="error-icon">⚠️</span>
            <span>{{ uploadError }}</span>
          </div>
        </div>

        <!-- 上传进度 -->
        <div
          v-else-if="isUploading"
          class="upload-progress-section"
        >
          <div class="progress-card">
            <div class="progress-header">
              <span class="file-name">{{ uploadedFile.name }}</span>
              <span class="progress-percent">{{ uploadProgress }}%</span>
            </div>
            <div class="progress-bar-wrapper">
              <div
                class="progress-bar"
                :style="{ width: `${uploadProgress}%` }"
              ></div>
            </div>
            <p class="progress-text">正在上传并解析文件...</p>
          </div>
        </div>

        <!-- 解析结果展示与编辑 -->
        <div
          v-else-if="hasParsedData"
          class="parsed-result-section"
        >
          <div class="result-card">
            <div class="result-header">
              <h2 class="result-title">解析结果</h2>
              <div class="result-actions">
                <button
                  v-if="!isEditing"
                  class="btn btn-secondary"
                  @click="isEditing = true"
                >
                  编辑
                </button>
                <button
                  v-else
                  class="btn btn-primary"
                  :disabled="!canSave"
                  @click="handleSaveEditedData"
                >
                  保存并分析
                </button>
                <button
                  class="btn btn-outline"
                  @click="handleClearFile"
                >
                  重新上传
                </button>
              </div>
            </div>

            <div class="result-content">
              <!-- 案件基本信息 -->
              <div class="info-section">
                <h3 class="section-title">案件基本信息</h3>
                <div class="info-grid">
                  <div class="info-item">
                    <label class="info-label">案件编号</label>
                    <input
                      v-if="isEditing"
                      v-model="editableData.case_id"
                      type="text"
                      class="info-input"
                    >
                    <span
                      v-else
                      class="info-value"
                    >{{ parsedData.case_id || '未提供' }}</span>
                  </div>
                  <div class="info-item">
                    <label class="info-label">案件类型</label>
                    <input
                      v-if="isEditing"
                      v-model="editableData.case_type"
                      type="text"
                      class="info-input"
                    >
                    <span
                      v-else
                      class="info-value"
                    >{{ parsedData.case_type || '帮信罪' }}</span>
                  </div>
                  <div class="info-item">
                    <label class="info-label">涉案金额</label>
                    <input
                      v-if="isEditing"
                      v-model="editableData.amount_involved"
                      type="text"
                      class="info-input"
                    >
                    <span
                      v-else
                      class="info-value"
                    >{{ parsedData.amount_involved || '未提供' }}</span>
                  </div>
                  <div class="info-item">
                    <label class="info-label">涉案人数</label>
                    <input
                      v-if="isEditing"
                      v-model="editableData.suspects_count"
                      type="text"
                      class="info-input"
                    >
                    <span
                      v-else
                      class="info-value"
                    >{{ parsedData.suspects_count || '未提供' }}</span>
                  </div>
                </div>
              </div>

              <!-- 案件事实描述 -->
              <div class="info-section">
                <h3 class="section-title">案件事实描述</h3>
                <textarea
                  v-if="isEditing"
                  v-model="editableData.fact_description"
                  class="fact-textarea"
                  rows="8"
                ></textarea>
                <div
                  v-else
                  class="fact-content"
                >
                  {{ parsedData.fact_description || '暂无事实描述' }}
                </div>
              </div>

              <!-- 关键证据 -->
              <div
                v-if="parsedData.key_evidence || editableData.key_evidence"
                class="info-section"
              >
                <h3 class="section-title">关键证据</h3>
                <textarea
                  v-if="isEditing"
                  v-model="editableData.key_evidence"
                  class="fact-textarea"
                  rows="6"
                ></textarea>
                <div
                  v-else
                  class="fact-content"
                >
                  {{ parsedData.key_evidence }}
                </div>
              </div>

              <!-- 嫌疑人信息 -->
              <div
                v-if="parsedData.suspect_info || editableData.suspect_info"
                class="info-section"
              >
                <h3 class="section-title">嫌疑人信息</h3>
                <textarea
                  v-if="isEditing"
                  v-model="editableData.suspect_info"
                  class="fact-textarea"
                  rows="4"
                ></textarea>
                <div
                  v-else
                  class="fact-content"
                >
                  {{ parsedData.suspect_info }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-page {
  padding: 2rem 0;
  min-height: calc(100vh - 56px);
  background: var(--bg-secondary, #f8fafc);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.page-header {
  margin-bottom: 2rem;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  font-family: inherit;
  color: var(--color-primary, #4f46e5);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  margin-bottom: 0.75rem;
}

.back-btn:hover {
  text-decoration: underline;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  margin: 0 0 0.5rem;
}

.page-subtitle {
  font-size: 1rem;
  color: var(--text-secondary, #64748b);
  margin: 0;
}

.upload-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

/* 拖放上传区域 */
.upload-section {
  width: 100%;
}

.drop-zone {
  border: 2px dashed var(--border-color, #e2e8f0);
  border-radius: var(--border-radius-lg, 12px);
  padding: 4rem 2rem;
  text-align: center;
  transition: all var(--transition-fast, 150ms ease);
  background: var(--bg-primary, #fff);
  cursor: pointer;
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: var(--color-primary, #4f46e5);
  background: rgba(79, 70, 229, 0.02);
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.upload-icon {
  font-size: 4rem;
  opacity: 0.6;
}

.drop-text {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0;
}

.drop-hint {
  font-size: 0.875rem;
  color: var(--text-tertiary, #94a3b8);
  margin: 0;
}

.file-select-btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: var(--color-primary, #4f46e5);
  color: white;
  border-radius: var(--border-radius, 8px);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast, 150ms ease);
}

.file-select-btn:hover {
  background: var(--color-primary-hover, #4338ca);
}

.file-input {
  display: none;
}

.format-hint {
  font-size: 0.875rem;
  color: var(--text-tertiary, #94a3b8);
  margin: 0;
}

.error-alert {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  color: var(--color-danger, #ef4444);
  background: rgba(239, 68, 68, 0.06);
  border-radius: var(--border-radius, 8px);
}

.error-icon {
  flex-shrink: 0;
}

/* 上传进度 */
.upload-progress-section {
  width: 100%;
}

.progress-card {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  padding: 2rem;
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.file-name {
  font-weight: 600;
  color: var(--text-primary, #1e293b);
}

.progress-percent {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-primary, #4f46e5);
}

.progress-bar-wrapper {
  width: 100%;
  height: 8px;
  background: var(--bg-tertiary, #f1f5f9);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary, #4f46e5), #7c3aed);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.875rem;
  color: var(--text-secondary, #64748b);
  margin: 0;
  text-align: center;
}

/* 解析结果 */
.parsed-result-section {
  width: 100%;
}

.result-card {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
  overflow: hidden;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-color, #e2e8f0);
}

.result-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0;
}

.result-actions {
  display: flex;
  gap: 0.75rem;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: var(--border-radius, 8px);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast, 150ms ease);
  border: none;
  font-family: inherit;
}

.btn-primary {
  background: var(--color-primary, #4f46e5);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover, #4338ca);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-tertiary, #f1f5f9);
  color: var(--text-primary, #1e293b);
}

.btn-secondary:hover {
  background: var(--border-color, #e2e8f0);
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border-color, #e2e8f0);
  color: var(--text-primary, #1e293b);
}

.btn-outline:hover {
  background: var(--bg-tertiary, #f1f5f9);
}

.result-content {
  padding: 1.5rem;
}

.info-section {
  margin-bottom: 2rem;
}

.info-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0 0 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--border-color, #e2e8f0);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary, #64748b);
}

.info-input {
  padding: 0.5rem;
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: var(--border-radius, 8px);
  font-size: 0.9375rem;
  font-family: inherit;
  transition: border-color var(--transition-fast, 150ms ease);
}

.info-input:focus {
  outline: none;
  border-color: var(--color-primary, #4f46e5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.info-value {
  font-size: 0.9375rem;
  color: var(--text-primary, #1e293b);
  padding: 0.5rem;
  background: var(--bg-secondary, #f8fafc);
  border-radius: var(--border-radius, 8px);
}

.fact-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: var(--border-radius, 8px);
  font-size: 0.9375rem;
  font-family: inherit;
  line-height: 1.6;
  resize: vertical;
  transition: border-color var(--transition-fast, 150ms ease);
}

.fact-textarea:focus {
  outline: none;
  border-color: var(--color-primary, #4f46e5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.fact-content {
  font-size: 0.9375rem;
  line-height: 1.7;
  color: var(--text-primary, #1e293b);
  padding: 1rem;
  background: var(--bg-secondary, #f8fafc);
  border-radius: var(--border-radius, 8px);
  white-space: pre-wrap;
}

@media (max-width: 768px) {
  .drop-zone {
    padding: 2rem 1rem;
  }

  .upload-icon {
    font-size: 3rem;
  }

  .drop-text {
    font-size: 1rem;
  }

  .result-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .result-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
