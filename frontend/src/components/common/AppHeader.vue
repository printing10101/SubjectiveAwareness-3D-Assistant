<script setup>
import { computed } from 'vue'

import { useRouter } from 'vue-router'

import { useAuthStore } from '../../stores/auth.js'

defineOptions({ name: 'AppHeader' })

const props = defineProps({
  title: {
    type: String,
    default: '主观明知分析系统',
  },
  isLoggedIn: {
    type: Boolean,
    default: false,
  },
  userName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['toggle-sidebar', 'logout'])

const router = useRouter()
const authStore = useAuthStore()

const displayTitle = computed(() => props.title)

const displayName = computed(() => props.userName || authStore.displayName)

function handleNavigateHome() {
  router.push('/main')
}

function handleToggleSidebar() {
  emit('toggle-sidebar')
}

function handleLogout() {
  emit('logout')
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <div class="header-left">
        <button
          v-if="isLoggedIn"
          class="header-sidebar-toggle"
          aria-label="切换侧边栏"
          @click="handleToggleSidebar"
        >
          <span class="toggle-icon"></span>
        </button>
        <div
          class="header-brand"
          @click="handleNavigateHome"
        >
          <span class="header-logo">⚖️</span>
          <span class="header-title">{{ displayTitle }}</span>
        </div>
      </div>

      <div class="header-right">
        <template v-if="isLoggedIn">
          <span class="header-user">{{ displayName }}</span>
          <button
            class="header-logout-btn"
            @click="handleLogout"
          >
            退出登录
          </button>
        </template>
        <template v-else>
          <button
            class="header-login-btn"
            @click="router.push('/login')"
          >
            登录
          </button>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--bg-primary, #fff);
  border-bottom: 1px solid var(--border-color, #e2e8f0);
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 56px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--border-radius, 8px);
  cursor: pointer;
  transition: background var(--transition-fast, 150ms ease);
}

.header-sidebar-toggle:hover {
  background: var(--bg-tertiary, #f1f5f9);
}

.toggle-icon {
  display: block;
  width: 18px;
  height: 2px;
  background: var(--text-primary, #1e293b);
  position: relative;
  border-radius: 2px;
}

.toggle-icon::before,
.toggle-icon::after {
  content: '';
  display: block;
  width: 18px;
  height: 2px;
  background: var(--text-primary, #1e293b);
  position: absolute;
  left: 0;
  border-radius: 2px;
  transition: transform 200ms ease;
}

.toggle-icon::before {
  top: -5px;
}

.toggle-icon::after {
  top: 5px;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
}

.header-logo {
  font-size: 1.375rem;
}

.header-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-user {
  font-size: 0.875rem;
  color: var(--text-secondary, #64748b);
}

.header-logout-btn,
.header-login-btn {
  font-size: 0.875rem;
  font-weight: 500;
  font-family: inherit;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: var(--border-radius, 8px);
  cursor: pointer;
  transition: all var(--transition-fast, 150ms ease);
}

.header-logout-btn {
  color: var(--text-secondary, #64748b);
  background: var(--bg-tertiary, #f1f5f9);
}

.header-logout-btn:hover {
  color: var(--color-danger, #ef4444);
  background: rgba(239, 68, 68, 0.08);
}

.header-login-btn {
  color: #fff;
  background: var(--color-primary, #4f46e5);
}

.header-login-btn:hover {
  background: var(--color-primary-hover, #4338ca);
}

@media (max-width: 767px) {
  .header-inner {
    padding: 0 1rem;
  }

  .header-title {
    font-size: 0.875rem;
  }
}
</style>