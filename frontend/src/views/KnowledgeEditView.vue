<script setup>
import { ref, computed, onMounted, watch } from 'vue'

import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { useRoute, useRouter } from 'vue-router'

import { useKnowledgeStore } from '../stores/knowledgeStore.js'

const route = useRoute()
const router = useRouter()
const store = useKnowledgeStore()

const isEditMode = computed(() => !!route.params.id)

const pageTitle = computed(() => (isEditMode.value ? '编辑知识' : '新建知识'))

const title = ref('')
const category = ref('')
const content = ref('')
const tagsInput = ref('')
const selectedTags = ref([])
const confidenceScore = ref(0.5)
const status = ref('draft')
const isSubmitting = ref(false)
const submitError = ref(null)
const isLoadingData = ref(false)
const loadError = ref(null)
const availableTags = ref([])
const isPreviewVisible = ref(false)
const isUnsavedChanges = ref(false)

const categoryOptions = [
  { value: 'criminal_law', label: '刑法' },
  { value: 'criminal_procedure_law', label: '刑事诉讼法' },
  { value: 'judicial_interpretation', label: '司法解释' },
  { value: 'evidence_analysis', label: '证据分析方法' },
  { value: 'legal_reasoning', label: '法律推理方法' },
  { value: 'case_comparison', label: '案例比较方法' },
  { value: 'precedent_case', label: '判例' },
  { value: 'typical_case', label: '典型案例' },
  { value: 'reference_case', label: '参考案例' },
]

const statusOptions = [
  { value: 'draft', label: '草稿' },
  { value: 'review', label: '审核中' },
  { value: 'published', label: '已审核' },
]

const formErrors = computed(() => {
  const errors = {}
  if (!title.value.trim()) {
    errors.title = '标题不能为空'
  } else if (title.value.trim().length > 200) {
    errors.title = '标题不能超过200个字符'
  }
  if (!category.value) {
    errors.category = '请选择分类'
  }
  if (!content.value.trim()) {
    errors.content = '内容不能为空'
  }
  return errors
})

const hasErrors = computed(() => Object.keys(formErrors.value).length > 0)

const canSubmit = computed(() => !hasErrors.value && !isSubmitting.value)

const tagSuggestions = computed(() => {
  const current = tagsInput.value.trim()
  if (!current) return availableTags.value.slice(0, 8)
  return availableTags.value
    .filter((t) => t.toLowerCase().includes(current.toLowerCase()) && !selectedTags.value.includes(t))
    .slice(0, 5)
})

watch([title, content, category], () => {
  isUnsavedChanges.value = true
})

function addTagFromInput() {
  const input = tagsInput.value.trim()
  if (input && !selectedTags.value.includes(input)) {
    selectedTags.value.push(input)
    if (!availableTags.value.includes(input)) {
      availableTags.value.push(input)
    }
    tagsInput.value = ''
  }
}

function addTag(tag) {
  if (!selectedTags.value.includes(tag)) {
    selectedTags.value.push(tag)
  }
  tagsInput.value = ''
}

function removeTag(tag) {
  const index = selectedTags.value.indexOf(tag)
  if (index !== -1) {
    selectedTags.value.splice(index, 1)
  }
}

function handleTagsKeydown(event) {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    addTagFromInput()
  }
}

function handleCancel() {
  if (isUnsavedChanges.value) {
    if (window.confirm('确定要取消吗？未保存的更改将会丢失。')) {
      router.push({ name: 'knowledge' })
    }
  } else {
    router.push({ name: 'knowledge' })
  }
}

async function handleSave() {
  if (hasErrors.value) return

  isSubmitting.value = true
  submitError.value = null

  const data = {
    title: title.value.trim(),
    category: category.value,
    content: content.value,
    tags: selectedTags.value,
    confidence_score: confidenceScore.value,
    status: status.value,
  }

  try {
    if (isEditMode.value) {
      await store.updateEntry(route.params.id, data)
    } else {
      await store.createEntry(data)
    }
    isUnsavedChanges.value = false
    router.push({ name: 'knowledge' })
  } catch (err) {
    submitError.value = err?.message || '保存失败，请稍后重试'
  } finally {
    isSubmitting.value = false
  }
}

function togglePreview() {
  isPreviewVisible.value = !isPreviewVisible.value
}

async function fetchAvailableTags() {
  try {
    await store.fetchTags()
    availableTags.value = store.tags
  } catch {
    availableTags.value = []
  }
}

async function loadEntry() {
  if (!isEditMode.value) return

  isLoadingData.value = true
  loadError.value = null

  try {
    await store.fetchEntry(route.params.id)
    const entry = store.currentEntry
    if (entry) {
      title.value = entry.title || ''
      category.value = entry.category || ''
      content.value = entry.content || ''
      selectedTags.value = entry.tags || []
      confidenceScore.value = entry.confidence_score ?? 0.5
      status.value = entry.status || 'draft'
    }
  } catch (err) {
    loadError.value = err?.message || '加载知识条目失败'
  } finally {
    isLoadingData.value = false
  }
}

onMounted(() => {
  fetchAvailableTags()
  loadEntry()
})
</script>

<template>
  <div class="edit-page">
    <!-- 加载状态 -->
    <div
      v-if="isLoadingData"
      class="loading-area"
    >
      <div class="loading-spinner"></div>
      <p>正在加载数据...</p>
    </div>

    <!-- 加载错误 -->
    <div
      v-else-if="loadError"
      class="error-area"
    >
      <div class="error-card card">
        <div class="error-icon-large">⚠️</div>
        <h2 class="error-title">加载失败</h2>
        <p class="error-desc">{{ loadError }}</p>
        <button
          class="btn btn-primary"
          @click="router.push({ name: 'knowledge' })"
        >
          返回列表
        </button>
      </div>
    </div>

    <!-- 编辑表单 -->
    <template v-else>
      <header class="edit-header">
        <h1 class="page-title">{{ pageTitle }}</h1>
        <p class="page-subtitle">
          {{ isEditMode ? '修改知识条目的内容和信息' : '创建新的知识条目' }}
        </p>
      </header>

      <div
        v-if="submitError"
        class="error-alert"
      >
        <span class="error-icon">!</span>
        <span class="error-text">{{ submitError }}</span>
        <button
          class="error-close"
          @click="submitError = null"
        >
          ×
        </button>
      </div>

      <!-- 基本信息表单 -->
      <div class="form-section card">
        <h2 class="section-title">基本信息</h2>

        <div class="form-grid">
          <div class="form-group">
            <label
              class="form-label"
              for="entry-title"
            >
              标题 <span class="required">*</span>
            </label>
            <input
              id="entry-title"
              v-model="title"
              type="text"
              class="form-input"
              :class="{ 'form-input--error': formErrors.title }"
              placeholder="请输入知识条目标题"
              maxlength="200"
            />
            <div
              v-if="formErrors.title"
              class="form-error"
            >
              {{ formErrors.title }}
            </div>
            <div class="form-field-footer">
              <span class="form-counter">{{ title.length }}/200</span>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group form-group--half">
              <label
                class="form-label"
                for="entry-category"
              >
                分类 <span class="required">*</span>
              </label>
              <select
                id="entry-category"
                v-model="category"
                class="form-select"
                :class="{ 'form-select--error': formErrors.category }"
              >
                <option
                  value=""
                  disabled
                >
                  请选择分类
                </option>
                <option
                  v-for="opt in categoryOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </option>
              </select>
              <div
                v-if="formErrors.category"
                class="form-error"
              >
                {{ formErrors.category }}
              </div>
            </div>

            <div class="form-group form-group--half">
              <label
                class="form-label"
                for="entry-status"
              >
                状态
              </label>
              <select
                id="entry-status"
                v-model="status"
                class="form-select"
              >
                <option
                  v-for="opt in statusOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">信心评分</label>
            <div class="confidence-slider">
              <input
                v-model.number="confidenceScore"
                type="range"
                min="0"
                max="1"
                step="0.05"
                class="slider-input"
              />
              <span class="slider-value">{{ (confidenceScore * 100).toFixed(0) }}%</span>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">标签</label>
            <div class="tags-input-wrapper">
              <div class="tags-display">
                <span
                  v-for="tag in selectedTags"
                  :key="tag"
                  class="tag-item"
                >
                  {{ tag }}
                  <button
                    class="tag-remove"
                    @click="removeTag(tag)"
                  >
                    ×
                  </button>
                </span>
                <input
                  v-model="tagsInput"
                  type="text"
                  class="tags-text-input"
                  placeholder="输入标签，按回车添加..."
                  @keydown="handleTagsKeydown"
                />
              </div>

              <div
                v-if="tagSuggestions.length > 0"
                class="tag-suggestions"
              >
                <button
                  v-for="suggestion in tagSuggestions"
                  :key="suggestion"
                  class="tag-suggestion-item"
                  @click="addTag(suggestion)"
                >
                  {{ suggestion }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Markdown 编辑器 -->
      <div class="editor-section card">
        <div class="editor-header">
          <h2 class="section-title">正文内容 <span class="required">*</span></h2>
          <button
            class="btn btn-secondary btn-sm"
            @click="togglePreview"
          >
            {{ isPreviewVisible ? '关闭预览' : '全屏预览' }}
          </button>
        </div>

        <div
          v-if="formErrors.content"
          class="form-error editor-error"
        >
          {{ formErrors.content }}
        </div>

        <MdEditor
          v-model="content"
          :language="'zh-CN'"
          :toolbars="[
            'bold', 'italic', 'strikethrough', 'title', '|',
            'quote', 'unorderedList', 'orderedList', 'code', '|',
            'link', 'image', 'table', '|',
            'preview', 'fullscreen',
          ]"
          :preview="true"
          style="height: 500px"
        />
      </div>

      <!-- 操作按钮 -->
      <div class="action-bar">
        <button
          class="btn btn-secondary"
          @click="handleCancel"
        >
          取消
        </button>
        <button
          class="btn btn-primary"
          :disabled="!canSubmit"
          @click="handleSave"
        >
          {{ isSubmitting ? '保存中...' : '保存' }}
        </button>
      </div>
    </template>

    <!-- 全屏预览弹窗 -->
    <Teleport to="body">
      <div
        v-if="isPreviewVisible"
        class="preview-overlay"
        @click.self="togglePreview"
      >
        <div class="preview-dialog">
          <div class="preview-header">
            <h2 class="preview-title">预览</h2>
            <button
              class="preview-close"
              @click="togglePreview"
            >
              ×
            </button>
          </div>
          <div class="preview-body">
            <MdEditor
              v-model="content"
              :language="'zh-CN'"
              :preview-only="true"
              style="height: calc(100vh - 100px)"
            />
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.edit-page {
  min-height: 100vh;
  background: var(--bg-secondary);
  padding: 2rem 1rem;
}

.edit-header {
  max-width: 900px;
  margin: 0 auto 1.5rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.page-subtitle {
  color: var(--text-secondary);
  font-size: 1rem;
}

/* 加载状态 */
.loading-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 1rem;
  color: var(--text-secondary);
}

/* 错误状态 */
.error-area {
  display: flex;
  justify-content: center;
  padding-top: 4rem;
}

.error-card {
  max-width: 480px;
  width: 100%;
  text-align: center;
  padding: 3rem 2rem;
}

.error-icon-large {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.error-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.error-desc {
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
}

/* 错误提示 */
.error-alert {
  max-width: 900px;
  margin: 0 auto 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--border-radius);
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

/* 表单区域 */
.form-section {
  max-width: 900px;
  margin: 0 auto 1.5rem;
  padding: 1.5rem 2rem;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--border-color);
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.required {
  color: var(--color-danger);
}

.form-input,
.form-select {
  padding: 0.625rem 0.875rem;
  font-size: 0.9rem;
  font-family: inherit;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: border-color var(--transition-fast);
  outline: none;
}

.form-input:focus,
.form-select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.form-input--error,
.form-select--error {
  border-color: var(--color-danger);
}

.form-input--error:focus,
.form-select--error:focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.form-select {
  cursor: pointer;
  appearance: auto;
}

.form-field-footer {
  display: flex;
  justify-content: flex-end;
}

.form-counter {
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.form-error {
  font-size: 0.8rem;
  color: var(--color-danger);
  margin-top: 0.125rem;
}

/* 信心评分滑块 */
.confidence-slider {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.slider-input {
  flex: 1;
  max-width: 300px;
  height: 6px;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.slider-value {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 45px;
}

/* 标签输入 */
.tags-input-wrapper {
  position: relative;
}

.tags-display {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.625rem;
  min-height: 42px;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  transition: border-color var(--transition-fast);
}

.tags-display:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.5rem 0.2rem 0.625rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  border: 1px solid rgba(79, 70, 229, 0.2);
  border-radius: 100px;
}

.tag-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  font-size: 0.75rem;
  font-family: inherit;
  color: var(--color-primary);
  background: none;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tag-remove:hover {
  background: rgba(79, 70, 229, 0.2);
}

.tags-text-input {
  flex: 1;
  min-width: 120px;
  border: none;
  background: none;
  font-size: 0.9rem;
  font-family: inherit;
  color: var(--text-primary);
  outline: none;
  padding: 0.125rem 0;
}

.tags-text-input::placeholder {
  color: var(--text-tertiary);
}

.tag-suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 0.25rem;
  padding: 0.375rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-md);
  z-index: 50;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.tag-suggestion-item {
  padding: 0.25rem 0.625rem;
  font-size: 0.8rem;
  font-family: inherit;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: none;
  border-radius: 100px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tag-suggestion-item:hover {
  background: rgba(79, 70, 229, 0.1);
  color: var(--color-primary);
}

/* 编辑器区域 */
.editor-section {
  max-width: 900px;
  margin: 0 auto 1.5rem;
  padding: 1.5rem 2rem;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--border-color);
}

.editor-header .section-title {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.editor-error {
  margin-bottom: 0.5rem;
}

/* 操作按钮 */
.action-bar {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

/* 预览弹窗 */
.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  z-index: 1000;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.preview-dialog {
  width: 100%;
  max-width: 1000px;
  max-height: 90vh;
  background: var(--bg-primary);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  animation: slideUp 0.2s ease;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.preview-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.preview-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
  transition: color var(--transition-fast);
}

.preview-close:hover {
  color: var(--text-primary);
}

.preview-body {
  padding: 1rem;
  overflow: hidden;
}

/* 响应式 */
@media (max-width: 767px) {
  .edit-page {
    padding: 1rem 0.75rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .form-section,
  .editor-section {
    padding: 1.25rem;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .preview-dialog {
    max-width: 100%;
    margin: 0.5rem;
  }
}
</style>