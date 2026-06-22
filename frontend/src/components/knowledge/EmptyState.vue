<script setup>
defineProps({
  hasFilters: Boolean,
})
</script>

<template>
  <div class="empty-area card">
    <div class="empty-icon">📖</div>
    <h3 class="empty-title">暂无知识条目</h3>
    <p class="empty-desc">
      {{
        hasFilters
          ? '没有匹配的知识条目，请调整筛选条件'
          : '点击上方"新建知识"按钮创建第一个知识条目'
      }}
    </p>
  </div>
</template>

<style scoped>
.empty-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-desc {
  color: var(--text-secondary);
  font-size: 0.9rem;
  max-width: 360px;
}
</style>
