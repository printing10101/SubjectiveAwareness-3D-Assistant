<script setup>
// 1. 导入语句 — 无
// 8. 生命周期钩子 — 无
</script>

<template>
  <div class="forbidden-page">
    <div class="forbidden-content">
      <div class="forbidden-icon">🔒</div>
      <h1 class="forbidden-code">403</h1>
      <h2 class="forbidden-title">Forbidden</h2>
      <p class="forbidden-desc">
        抱歉，您没有权限访问此页面
      </p>
      <div class="forbidden-reasons">
        <h3 class="reasons-title">可能的原因</h3>
        <ul class="reasons-list">
          <li>您未登录或登录已过期</li>
          <li>您的账号权限不足，需要管理员权限</li>
          <li>您尝试访问的资源已被限制</li>
        </ul>
      </div>
      <div class="forbidden-actions">
        <router-link to="/main" class="btn btn-primary">
          返回首页
        </router-link>
        <a href="mailto:admin@example.com" class="btn btn-outline">
          联系管理员
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.forbidden-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 2rem 1rem;
}

.forbidden-content {
  max-width: 500px;
  width: 100%;
  text-align: center;
  background: white;
  padding: 3rem 2rem;
  border-radius: var(--border-radius-lg, 12px);
  box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
}

.forbidden-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.forbidden-code {
  font-size: 5rem;
  font-weight: 700;
  color: var(--color-primary, #4f46e5);
  margin: 0;
  line-height: 1;
}

.forbidden-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  margin: 0.5rem 0;
}

.forbidden-desc {
  font-size: 1.125rem;
  color: var(--text-secondary, #6b7280);
  margin-bottom: 2rem;
}

.forbidden-reasons {
  text-align: left;
  padding: 1.25rem;
  background: #fef3c7;
  border-radius: var(--border-radius, 8px);
  border-left: 4px solid #eab308;
  margin-bottom: 2rem;
}

.reasons-title {
  font-size: 1rem;
  font-weight: 600;
  color: #92400e;
  margin-bottom: 0.75rem;
}

.reasons-list {
  padding-left: 1.25rem;
  color: #78350f;
  margin: 0;
}

.reasons-list li {
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.forbidden-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.btn {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  font-weight: 500;
  border-radius: var(--border-radius, 8px);
  cursor: pointer;
  transition: all var(--transition-fast, 0.2s);
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: var(--color-primary, #4f46e5);
  color: white;
  border: none;
}

.btn-primary:hover {
  background: var(--color-primary-dark, #4338ca);
  transform: translateY(-1px);
}

.btn-outline {
  background: transparent;
  color: var(--color-primary, #4f46e5);
  border: 2px solid var(--color-primary, #4f46e5);
}

.btn-outline:hover {
  background: var(--color-primary, #4f46e5);
  color: white;
}

@media (max-width: 768px) {
  .forbidden-content {
    padding: 2rem 1.5rem;
  }

  .forbidden-code {
    font-size: 3.5rem;
  }

  .forbidden-title {
    font-size: 1.5rem;
  }

  .forbidden-desc {
    font-size: 1rem;
  }

  .forbidden-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .forbidden-page {
    padding: 1rem 0.5rem;
  }

  .forbidden-content {
    padding: 1.5rem 1rem;
  }

  .forbidden-icon {
    font-size: 3rem;
  }

  .forbidden-code {
    font-size: 2.5rem;
  }
}
</style>
