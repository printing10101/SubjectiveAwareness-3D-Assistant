<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '文档文本将在此处展示，您可以直接编辑、修改和格式化...\n\n或者直接在此输入案件事实文本' },
})

const emit = defineEmits(['update:modelValue', 'clear'])

const editorRef = ref(null)
const internalContent = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  if (editorRef.value && editorRef.value.innerText !== val) {
    editorRef.value.innerHTML = val.replace(/\n/g, '<br>')
  }
  internalContent.value = val
})

function handleInput() {
  if (editorRef.value) {
    const text = editorRef.value.innerText
    internalContent.value = text
    emit('update:modelValue', text)
  }
}

function execCommand(cmd, value = null) {
  document.execCommand(cmd, false, value)
}

function handleClear() {
  if (editorRef.value) {
    editorRef.value.innerHTML = ''
    internalContent.value = ''
    emit('update:modelValue', '')
    emit('clear')
  }
}

defineExpose({ editorRef, focus: () => editorRef.value?.focus() })
</script>

<template>
  <div class="editor-section card">
    <div class="editor-header">
      <h3 class="section-title">案件事实文本</h3>
      <div class="editor-toolbar">
        <button class="toolbar-btn" title="加粗" @click="execCommand('bold')"><strong>B</strong></button>
        <button class="toolbar-btn" title="斜体" @click="execCommand('italic')"><em>I</em></button>
        <button class="toolbar-btn" title="下划线" @click="execCommand('underline')"><u>U</u></button>
        <span class="toolbar-sep"></span>
        <button class="toolbar-btn" title="清除格式" @click="execCommand('removeFormat')">清除</button>
        <button class="toolbar-btn toolbar-btn--danger" title="清空内容" @click="handleClear">清空</button>
      </div>
    </div>
    <div
      ref="editorRef"
      class="rich-editor"
      contenteditable="true"
      :data-placeholder="placeholder"
      @input="handleInput"
    ></div>
    <div class="editor-footer">
      <span class="char-count">{{ internalContent.length }} 字符</span>
      <span v-if="internalContent.trim()" class="char-count--valid">文本已就绪</span>
    </div>
  </div>
</template>

<style scoped>
.editor-section { padding: 1.5rem; display: flex; flex-direction: column; }
.editor-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.75rem; }
.editor-toolbar { display: flex; align-items: center; gap: 0.25rem; flex-wrap: wrap; }
.toolbar-btn { padding: 0.375rem 0.625rem; font-size: 0.8rem; font-family: inherit; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px; cursor: pointer; color: var(--text-primary); transition: all var(--transition-fast); line-height: 1; }
.toolbar-btn:hover { background: var(--bg-tertiary); border-color: var(--text-tertiary); }
.toolbar-btn--danger:hover { color: var(--color-danger); border-color: var(--color-danger); }
.toolbar-sep { width: 1px; height: 18px; background: var(--border-color); margin: 0 0.25rem; }
.rich-editor { min-height: 300px; max-height: 500px; padding: 1rem; font-size: 0.95rem; line-height: 1.8; border: 2px solid var(--border-color); border-radius: var(--border-radius); overflow-y: auto; outline: none; transition: border-color var(--transition-fast); }
.rich-editor:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1); }
.rich-editor:empty::before { content: attr(data-placeholder); color: var(--text-tertiary); pointer-events: none; }
.editor-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem; }
.char-count { font-size: 0.8rem; color: var(--text-tertiary); }
.char-count--valid { color: var(--color-success); font-weight: 500; }
@media (max-width: 768px) { .editor-header { flex-direction: column; } }
</style>
