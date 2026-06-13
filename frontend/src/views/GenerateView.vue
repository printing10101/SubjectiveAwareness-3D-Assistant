<script setup>
// 1. 导入语句
// 8. 生命周期钩子 — 无
</script>

<template>
  <div class="generate-page">
    <div class="generate-content">
      <div class="generate-icon">📊</div>
      <h1 class="generate-title">需要生成分析结果</h1>
      <p class="generate-desc">
        您尝试查看的报告还没有对应的分析数据。请先在主界面输入案件事实并执行分析。
      </p>

      <div class="generate-steps">
        <h3 class="steps-title">操作步骤</h3>
        <ol class="steps-list">
          <li>返回主界面，输入或粘贴案件事实描述</li>
          <li>点击"开始分析"按钮等待分析完成</li>
          <li>分析完成后即可查看详细报告</li>
        </ol>
      </div>

      <div class="generate-actions">
        <router-link to="/main" class="btn btn-primary btn-lg">
          前往分析页面
        </router-link>
        <router-link to="/" class="btn btn-outline btn-lg">
          返回首页
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.generate-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 2rem 1rem;
}

.generate-content {
  max-width: 500px;
  width: 100%;
  text-align: center;
  background: white;
  padding: 3rem 2rem;
  border-radius: var(--border-radius-lg, 12px);
  box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
}

.generate-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.generate-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary, #1f2937);
  margin-bottom: 0.5rem;
}

.generate-desc {
  font-size: 1.125rem;
  color: var(--text-secondary, #6b7280);
  margin-bottom: 2rem;
  line-height: 1.8;
}

.generate-steps {
  text-align: left;
  padding: 1.25rem;
  background: #e0e7ff;
  border-radius: var(--border-radius, 8px);
  border-left: 4px solid #4f46e5;
  margin-bottom: 2rem;
}

.steps-title {
  font-size: 1rem;
  font-weight: 600;
  color: #3730a3;
  margin-bottom: 0.75rem;
}

.steps-list {
  padding-left: 1.25rem;
  color: #312e81;
  margin: 0;
}

.steps-list li {
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  line-height: 1.6;
}

.generate-actions {
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
  .generate-content {
    padding: 2rem 1.5rem;
  }

  .generate-title {
    font-size: 1.5rem;
  }

  .generate-desc {
    font-size: 1rem;
  }

  .generate-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .generate-page {
    padding: 1rem 0.5rem;
  }

  .generate-content {
    padding: 1.5rem 1rem;
  }

  .generate-icon {
    font-size: 3rem;
  }
}
</style>
