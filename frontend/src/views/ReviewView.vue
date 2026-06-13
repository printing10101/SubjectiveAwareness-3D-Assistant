<script setup>
import { ref, computed, nextTick } from 'vue'

import axios from 'axios'
import { useRouter } from 'vue-router'

import { useAnalysisStore } from '../stores/analysisStore.js'

const router = useRouter()
const store = useAnalysisStore()

const ALLOWED_TYPES = ['.pdf', '.docx', '.doc']
const MAX_FILE_SIZE = 20 * 1024 * 1024

const isDragOver = ref(false)
const uploadProgress = ref(0)
const isUploading = ref(false)
const uploadError = ref('')
const uploadedFile = ref(null)

const extractProgress = ref(0)
const isExtracting = ref(false)
const extractError = ref('')

const editorContent = ref('')
const editorRef = ref(null)

const isExtractingEntities = ref(false)
const entityExtractError = ref('')
const extractionResult = ref(null)

const isAnalyzing = ref(false)
const analysisError = ref('')

const activeTab = ref('editor')

const canAnalyze = computed(() => editorContent.value.trim().length > 10 && !isAnalyzing.value)

const fileSizeLabel = computed(() => {
  if (!uploadedFile.value) return ''
  const size = uploadedFile.value.size
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(2)} MB`
})

function formatConfidence(val) {
  return `${(val * 100).toFixed(1)  }%`
}

function getConfidenceColor(val) {
  if (val >= 0.8) return 'confidence-high'
  if (val >= 0.5) return 'confidence-mid'
  return 'confidence-low'
}

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
  if (files.length > 0) {
    validateAndUpload(files[0])
  }
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length > 0) {
    validateAndUpload(files[0])
  }
  e.target.value = ''
}

function validateAndUpload(file) {
  uploadError.value = ''
  extractError.value = ''

  const ext = `.${  file.name.split('.').pop().toLowerCase()}`
  if (!ALLOWED_TYPES.includes(ext)) {
    uploadError.value = `不支持的文件格式: ${ext}。支持的格式: ${ALLOWED_TYPES.join(', ')}`
    return
  }

  if (file.size > MAX_FILE_SIZE) {
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
      editorContent.value = response.data.text
      activeTab.value = 'editor'

      nextTick(() => {
        if (editorRef.value) {
          editorRef.value.innerHTML = response.data.text.replace(/\n/g, '<br>')
        }
      })
    }, 300)
  } catch (error) {
    isUploading.value = false
    isExtracting.value = false
    uploadError.value = error.message || '文档上传失败，请重试'
    uploadedFile.value = null
  }
}

function handleEditorInput() {
  if (editorRef.value) {
    editorContent.value = editorRef.value.innerText
  }
}

function handleClearContent() {
  editorContent.value = ''
  if (editorRef.value) {
    editorRef.value.innerHTML = ''
  }
  extractionResult.value = null
  uploadedFile.value = null
  uploadError.value = ''
  extractError.value = ''
}

async function handleExtractEntities() {
  if (!editorContent.value.trim()) return

  isExtractingEntities.value = true
  entityExtractError.value = ''

  try {
    const response = await axios.post('/api/extract_entities', {
      text: editorContent.value,
    })
    extractionResult.value = response.data
  } catch (error) {
    entityExtractError.value = error.message || '实体抽取失败，请重试'
  } finally {
    isExtractingEntities.value = false
  }
}

function updateEntity(category, index, field, value) {
  if (extractionResult.value && extractionResult.value.entities[category]) {
    extractionResult.value.entities[category][index][field] = value
  }
}

function removeEntity(category, index) {
  if (extractionResult.value && extractionResult.value.entities[category]) {
    extractionResult.value.entities[category].splice(index, 1)
    extractionResult.value.entity_count = Math.max(0, extractionResult.value.entity_count - 1)
  }
}

function addEntity() {
  if (!extractionResult.value) {
    extractionResult.value = {
      entities: {},
      relations: [],
      entity_count: 0,
      relation_count: 0,
    }
  }
  if (!extractionResult.value.entities['自定义']) {
    extractionResult.value.entities['自定义'] = []
  }
  extractionResult.value.entities['自定义'].push({
    type: '自定义',
    value: '',
    confidence: 1.0,
  })
  extractionResult.value.entity_count++
}

async function handleStartAnalysis() {
  if (!canAnalyze.value) return

  isAnalyzing.value = true
  analysisError.value = ''

  try {
    const response = await axios.post('/api/analyze', {
      case_text: editorContent.value,
    })

    store.setAnalysisResult(response.data)
    store.setCaseText(editorContent.value)
    router.push('/report')
  } catch (error) {
    analysisError.value = error.message || '分析失败，请稍后重试'
  } finally {
    isAnalyzing.value = false
  }
}

function hasEntities() {
  return extractionResult.value &&
    extractionResult.value.entities &&
    Object.keys(extractionResult.value.entities).length > 0
}

function getEntityKeys() {
  if (!extractionResult.value || !extractionResult.value.entities) return []
  return Object.keys(extractionResult.value.entities)
}
</script>

<template>
  <div class="review-page">
    <header class="review-header">
      <h1 class="review-title">
        智能阅卷系统
      </h1>
      <p class="review-subtitle">
        上传案件文档，自动提取文本与实体信息，辅助人工阅卷
      </p>
    </header>

    <div class="review-content">
      <!-- 错误提示 -->
      <div
        v-if="uploadError || extractError || entityExtractError || analysisError"
        class="error-alert"
      >
        <span class="error-icon">!</span>
        <span class="error-text">{{ uploadError || extractError || entityExtractError || analysisError }}</span>
        <button
          class="error-close"
          @click="uploadError = ''; extractError = ''; entityExtractError = ''; analysisError = ''"
        >
          ×
        </button>
      </div>

      <div class="review-grid">
        <!-- 左栏：上传与文本 -->
        <div class="review-left">
          <!-- 文件上传区 -->
          <div class="upload-section card">
            <h3 class="section-title">
              文档上传
            </h3>
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
                <div class="drop-icon">
                  📄
                </div>
                <p class="drop-text">
                  拖放文件到此处，或点击上传
                </p>
                <p class="drop-hint">
                  支持 PDF、DOCX、DOC 格式，最大 20MB
                </p>
              </template>
              <template v-else-if="isUploading">
                <div class="upload-progress">
                  <div class="upload-spinner" ></div>
                  <p class="upload-status">
                    正在上传... {{ uploadProgress }}%
                  </p>
                  <div class="progress-bar">
                    <div
                      class="progress-fill"
                      :style="{ width: uploadProgress + '%' }"
                    ></div>
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
                  <button
                    class="file-remove"
                    @click.stop="uploadedFile = null; uploadProgress = 0"
                  >
                    ×
                  </button>
                </div>
              </template>
              <template v-else-if="isExtracting">
                <div class="upload-progress">
                  <div class="upload-spinner" ></div>
                  <p class="upload-status">
                    正在提取文本... {{ extractProgress }}%
                  </p>
                  <div class="progress-bar">
                    <div
                      class="progress-fill"
                      :style="{ width: extractProgress + '%' }"
                    ></div>
                  </div>
                </div>
              </template>
            </div>

            <div
              v-if="uploadedFile && !isUploading && !isExtracting"
              class="upload-actions"
            >
              <button
                class="btn btn-secondary btn-sm"
                @click="uploadedFile = null; uploadProgress = 0"
              >
                重新选择
              </button>
            </div>
          </div>

          <!-- 案件事实编辑区 -->
          <div class="editor-section card">
            <div class="editor-header">
              <h3 class="section-title">
                案件事实文本
              </h3>
              <div class="editor-toolbar">
                <button
                  class="toolbar-btn"
                  title="加粗"
                  @click="document.execCommand('bold')"
                >
                  <strong>B</strong>
                </button>
                <button
                  class="toolbar-btn"
                  title="斜体"
                  @click="document.execCommand('italic')"
                >
                  <em>I</em>
                </button>
                <button
                  class="toolbar-btn"
                  title="下划线"
                  @click="document.execCommand('underline')"
                >
                  <u>U</u>
                </button>
                <span class="toolbar-sep" ></span>
                <button
                  class="toolbar-btn"
                  title="清除格式"
                  @click="document.execCommand('removeFormat')"
                >
                  清除
                </button>
                <button
                  class="toolbar-btn toolbar-btn--danger"
                  title="清空内容"
                  @click="handleClearContent"
                >
                  清空
                </button>
              </div>
            </div>
            <div
              ref="editorRef"
              class="rich-editor"
              contenteditable="true"
              :data-placeholder="'文档文本将在此处展示，您可以直接编辑、修改和格式化...\n\n或者直接在此输入案件事实文本'"
              @input="handleEditorInput"
            ></div>
            <div class="editor-footer">
              <span class="char-count">{{ editorContent.length }} 字符</span>
              <span
                v-if="editorContent.trim()"
                class="char-count--valid"
              >文本已就绪</span>
            </div>
          </div>
        </div>

        <!-- 右栏：实体抽取与操作 -->
        <div class="review-right">
          <!-- 信息抽取操作区 -->
          <div class="extract-section card">
            <h3 class="section-title">
              信息抽取
            </h3>
            <p class="section-desc">
              从案件事实文本中自动抽取实体和关系信息
            </p>
            <button
              class="btn btn-primary btn-extract"
              :disabled="!editorContent.trim() || isExtractingEntities"
              @click="handleExtractEntities"
            >
              <span
                v-if="isExtractingEntities"
                class="btn-loading"
              >
                <span class="loading-spinner-small" ></span>
                抽取中...
              </span>
              <span v-else>开始抽取</span>
            </button>
          </div>

          <!-- 抽取结果展示 -->
          <div
            v-if="hasEntities()"
            class="result-section card"
          >
            <div class="result-header">
              <h3 class="section-title">
                抽取结果
              </h3>
              <span class="result-count">
                {{ extractionResult.entity_count }} 实体 / {{ extractionResult.relation_count }} 关系
              </span>
            </div>

            <div class="entity-categories">
              <div
                v-for="category in getEntityKeys()"
                :key="category"
                class="entity-category"
              >
                <h4 class="category-title">
                  {{ category }}
                </h4>
                <div class="entity-list">
                  <div
                    v-for="(entity, index) in extractionResult.entities[category]"
                    :key="category + '-' + index"
                    class="entity-card"
                  >
                    <div class="entity-header">
                      <span class="entity-type">{{ entity.type }}</span>
                      <span
                        class="entity-confidence"
                        :class="getConfidenceColor(entity.confidence)"
                      >{{ formatConfidence(entity.confidence) }}</span>
                    </div>
                    <div class="entity-body">
                      <input
                        class="entity-value-input"
                        :value="entity.value"
                        placeholder="实体值"
                        @input="updateEntity(category, index, 'value', $event.target.value)"
                      />
                    </div>
                    <button
                      class="entity-remove"
                      title="删除此实体"
                      @click="removeEntity(category, index)"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="entity-actions">
              <button
                class="btn btn-secondary btn-sm"
                @click="addEntity"
              >
                + 添加实体
              </button>
            </div>

            <!-- 关系列表 -->
            <div
              v-if="extractionResult.relations.length > 0"
              class="relations-section"
            >
              <h4 class="category-title">
                实体关系
              </h4>
              <div class="relations-list">
                <div
                  v-for="(rel, index) in extractionResult.relations"
                  :key="'rel-' + index"
                  class="relation-card"
                >
                  <span class="relation-from">{{ rel.from }}</span>
                  <span class="relation-arrow">→</span>
                  <span class="relation-type">{{ rel.type }}</span>
                  <span class="relation-arrow">→</span>
                  <span class="relation-to">{{ rel.to }}</span>
                  <span
                    v-if="rel.amount"
                    class="relation-amount"
                  >({{ rel.amount }}元)</span>
                  <span
                    class="relation-conf"
                    :class="getConfidenceColor(rel.confidence || 0.5)"
                  >
                    {{ formatConfidence(rel.confidence || 0.5) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 没有抽取结果时的占位 -->
          <div
            v-else
            class="placeholder-card card"
          >
            <div class="placeholder-icon">
              🔍
            </div>
            <h3 class="placeholder-title">
              尚未进行信息抽取
            </h3>
            <p class="placeholder-desc">
              上传文档后点击"开始抽取"<br/>自动识别案件关键实体
            </p>
          </div>

          <!-- 开始分析按钮 -->
          <button
            class="analyze-btn"
            :disabled="!canAnalyze"
            @click="handleStartAnalysis"
          >
            <span
              v-if="isAnalyzing"
              class="analyze-btn-loading"
            >
              <span class="loading-spinner-small" ></span>
              分析中...
            </span>
            <span v-else>开始分析 →</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.review-page {
  min-height: 100vh;
  background: var(--bg-secondary);
  padding: 2rem 1rem;
}

.review-header {
  text-align: center;
  margin-bottom: 2rem;
}

.review-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.review-subtitle {
  color: var(--text-secondary);
  font-size: 1.125rem;
}

.review-content {
  max-width: 1400px;
  margin: 0 auto;
}

.error-alert {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--border-radius);
  margin-bottom: 1.5rem;
  animation: shake 0.3s ease;
}

.error-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: var(--color-danger);
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.error-text {
  flex: 1;
  color: #991b1b;
  font-size: 0.9rem;
}

.error-close {
  background: none;
  border: none;
  color: #991b1b;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.review-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 1024px) {
  .review-grid {
    grid-template-columns: 3fr 2fr;
    gap: 2rem;
  }
}

/* 左栏 */
.review-left {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 上传区域 */
.upload-section {
  padding: 1.5rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}

.section-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 1rem;
}

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

.drop-zone:hover {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.03);
}

.drop-zone.drag-over {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  transform: scale(1.01);
}

.drop-zone.has-file {
  border-style: solid;
  border-color: var(--color-success);
  background: #f0fdf4;
  cursor: default;
  padding: 1.25rem 1.5rem;
  min-height: auto;
}

.file-input-hidden {
  display: none;
}

.drop-icon {
  font-size: 3rem;
  margin-bottom: 0.75rem;
}

.drop-text {
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.drop-hint {
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.upload-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--bg-tertiary);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.upload-status {
  font-size: 0.9rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.progress-bar {
  width: 100%;
  max-width: 240px;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), #7c3aed);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
}

.file-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.file-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.125rem;
  min-width: 0;
}

.file-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.file-size {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.file-remove {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0 0.25rem;
  line-height: 1;
  transition: color var(--transition-fast);
}

.file-remove:hover {
  color: var(--color-danger);
}

.upload-actions {
  margin-top: 0.75rem;
  display: flex;
  gap: 0.5rem;
}

/* 编辑器区域 */
.editor-section {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
}

.editor-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.toolbar-btn {
  padding: 0.375rem 0.625rem;
  font-size: 0.8rem;
  font-family: inherit;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-primary);
  transition: all var(--transition-fast);
  line-height: 1;
}

.toolbar-btn:hover {
  background: var(--bg-tertiary);
  border-color: var(--text-tertiary);
}

.toolbar-btn--danger:hover {
  color: var(--color-danger);
  border-color: var(--color-danger);
}

.toolbar-sep {
  width: 1px;
  height: 18px;
  background: var(--border-color);
  margin: 0 0.25rem;
}

.rich-editor {
  min-height: 300px;
  max-height: 500px;
  padding: 1rem;
  font-size: 0.95rem;
  line-height: 1.8;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow-y: auto;
  outline: none;
  transition: border-color var(--transition-fast);
}

.rich-editor:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.rich-editor:empty::before {
  content: attr(data-placeholder);
  color: var(--text-tertiary);
  pointer-events: none;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
}

.char-count {
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.char-count--valid {
  color: var(--color-success);
  font-weight: 500;
}

/* 右栏 */
.review-right {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 抽取操作区 */
.extract-section {
  padding: 1.5rem;
}

.btn-extract {
  width: 100%;
}

.btn-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.loading-spinner-small {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* 结果展示区 */
.result-section {
  padding: 1.5rem;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.result-count {
  font-size: 0.8rem;
  color: var(--text-tertiary);
  font-weight: 500;
}

.entity-categories {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 400px;
  overflow-y: auto;
}

.entity-category {
  padding: 0.75rem;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
}

.category-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
  padding-bottom: 0.375rem;
  border-bottom: 1px solid var(--border-color);
}

.entity-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.entity-card {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.625rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  transition: all var(--transition-fast);
  position: relative;
}

.entity-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.entity-header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
}

.entity-type {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  white-space: nowrap;
}

.entity-confidence {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  white-space: nowrap;
}

.confidence-high {
  color: #166534;
  background: #dcfce7;
}

.confidence-mid {
  color: #92400e;
  background: #fef3c7;
}

.confidence-low {
  color: #991b1b;
  background: #fef2f2;
}

.entity-body {
  flex: 1;
  min-width: 0;
}

.entity-value-input {
  width: 100%;
  padding: 0.25rem 0.375rem;
  font-size: 0.85rem;
  font-family: inherit;
  color: var(--text-primary);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 3px;
  outline: none;
  transition: all var(--transition-fast);
}

.entity-value-input:hover {
  border-color: var(--border-color);
}

.entity-value-input:focus {
  border-color: var(--color-primary);
  background: white;
}

.entity-remove {
  background: none;
  border: none;
  font-size: 1rem;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0 0.125rem;
  line-height: 1;
  transition: color var(--transition-fast);
  flex-shrink: 0;
}

.entity-remove:hover {
  color: var(--color-danger);
}

.entity-actions {
  margin-top: 0.75rem;
  display: flex;
  gap: 0.5rem;
}

/* 关系列表 */
.relations-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.relations-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.relation-card {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-secondary);
  border-radius: 6px;
  font-size: 0.85rem;
  flex-wrap: wrap;
}

.relation-from,
.relation-to {
  font-weight: 600;
  color: var(--text-primary);
}

.relation-arrow {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.relation-type {
  color: var(--color-primary);
  font-weight: 500;
  background: rgba(79, 70, 229, 0.06);
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
}

.relation-amount {
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.relation-conf {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  margin-left: auto;
}

/* 占位卡片 */
.placeholder-card {
  padding: 2rem;
  text-align: center;
}

.placeholder-icon {
  font-size: 3rem;
  margin-bottom: 0.75rem;
}

.placeholder-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.placeholder-desc {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* 开始分析按钮 */
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

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 14px 20px -3px rgba(79, 70, 229, 0.3);
}

.analyze-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.analyze-btn-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

@media (max-width: 768px) {
  .review-title {
    font-size: 1.5rem;
  }

  .review-subtitle {
    font-size: 0.95rem;
  }

  .editor-header {
    flex-direction: column;
  }

  .entity-card {
    flex-wrap: wrap;
  }

  .relation-card {
    font-size: 0.8rem;
  }
}
</style>
