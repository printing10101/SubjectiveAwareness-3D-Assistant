<script setup>
defineProps({
  selectedTags: Array,
})

const emit = defineEmits(['removeTag'])
</script>

<template>
  <div
    v-if="selectedTags.length > 0"
    class="active-tags"
  >
    <span class="active-tags-label">已选标签：</span>
    <span
      v-for="tag in selectedTags"
      :key="tag"
      class="active-tag"
    >
      {{ tag }}
      <button
        class="active-tag-remove"
        @click="emit('removeTag', tag)"
      >
        ×
      </button>
    </span>
  </div>
</template>

<style scoped>
.active-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  margin-bottom: 1rem;
  padding: 0.5rem 0;
}

.active-tags-label {
  font-size: 0.8rem;
  color: var(--text-tertiary);
  font-weight: 500;
}

.active-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem 0.25rem 0.625rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  border: 1px solid rgba(79, 70, 229, 0.2);
  border-radius: 100px;
}

.active-tag-remove {
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

.active-tag-remove:hover {
  background: rgba(79, 70, 229, 0.2);
}
</style>
