<script setup>
// 1. 导入语句
import { ref } from 'vue'

import * as Sentry from '@sentry/vue'
import { useRouter } from 'vue-router'

import { setToken } from '../utils/auth.js'

// 4. 组合式函数
const router = useRouter()

// 5. 响应式数据
const username = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMsg = ref('')

// 7. 方法
async function handleLogin() {
  errorMsg.value = ''
  isLoading.value = true

  // 记录用户登录操作（密码字段绝不发送）
  Sentry.addBreadcrumb({
    category: 'auth',
    level: 'info',
    message: 'login_submitted',
    data: { username: username.value },
  })

  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error?.detail || '登录失败')
    }

    const data = await response.json()
    setToken(data?.access_token)

    const redirect = new URLSearchParams(window.location.search).get('redirect')
    router.push(redirect || '/main')
  } catch (error) {
    errorMsg.value = error?.message || '登录失败，请检查用户名和密码'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-content">
      <div class="login-header">
        <h1 class="login-title">登录</h1>
        <p class="login-subtitle">AI辅助分析系统</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label" for="username">用户名</label>
          <input
            id="username"
            v-model="username"
            type="text"
            class="form-input"
            placeholder="请输入用户名"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="password">密码</label>
          <input
            id="password"
            v-model="password"
            type="password"
            class="form-input"
            placeholder="请输入密码"
            required
          />
        </div>

        <div v-if="errorMsg" class="form-error">
          {{ errorMsg }}
        </div>

        <button
          type="submit"
          class="btn btn-primary btn-lg login-btn"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="loading-spinner"></span>
          {{ isLoading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem 1rem;
}

.login-content {
  max-width: 400px;
  width: 100%;
  background: white;
  padding: 2.5rem;
  border-radius: var(--border-radius-lg, 12px);
  box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary, #1f2937);
  margin-bottom: 0.5rem;
}

.login-subtitle {
  font-size: 1rem;
  color: var(--text-secondary, #6b7280);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary, #1f2937);
}

.form-input {
  padding: 0.75rem 1rem;
  font-size: 1rem;
  border: 1px solid #d1d5db;
  border-radius: var(--border-radius, 8px);
  transition: border-color var(--transition-fast, 0.2s);
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary, #4f46e5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.form-error {
  padding: 0.75rem;
  background: #fee2e2;
  border-radius: var(--border-radius, 8px);
  color: #991b1b;
  font-size: 0.875rem;
}

.login-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading-spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .login-content {
    padding: 2rem 1.5rem;
  }

  .login-title {
    font-size: 1.75rem;
  }
}

@media (max-width: 480px) {
  .login-page {
    padding: 1rem 0.5rem;
  }

  .login-content {
    padding: 1.5rem 1rem;
  }

  .login-title {
    font-size: 1.5rem;
  }
}
</style>
