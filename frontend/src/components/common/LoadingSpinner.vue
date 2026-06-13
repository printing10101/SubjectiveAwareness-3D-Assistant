<script setup>
defineOptions({ name: 'LoadingSpinner' })

const props = defineProps({
  message: {
    type: String,
    default: '加载中...',
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value),
  },
})

const sizeMap = {
  sm: '28px',
  md: '40px',
  lg: '56px',
}

const spinnerSize = sizeMap[props.size] || sizeMap.md
</script>

<template>
  <div
    class="loading-spinner-wrapper"
    role="status"
    aria-live="polite"
  >
    <div
      class="loading-spinner-circle"
      :style="{ width: spinnerSize, height: spinnerSize }"
    ></div>
    <p
      v-if="message"
      class="loading-spinner-text"
    >
      {{ message }}
    </p>
  </div>
</template>

<style scoped>
.loading-spinner-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem;
}

.loading-spinner-circle {
  border: 3px solid var(--bg-tertiary, #f1f5f9);
  border-top-color: var(--color-primary, #4f46e5);
  border-radius: 50%;
  animation: spinner-rotate 0.8s linear infinite;
}

.loading-spinner-text {
  font-size: 0.875rem;
  color: var(--text-secondary, #64748b);
  margin: 0;
}

@keyframes spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}
</style>