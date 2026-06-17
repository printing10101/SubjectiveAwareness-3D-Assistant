<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'

import { useRoute, useRouter } from 'vue-router'

// 系统级免责声明文本（与后端 OpenAPI description 保持完全一致）
const SYSTEM_DISCLAIMER =
  '本系统为辅助参考工具，不构成法律意见。所有结论须经人工审查。'

const route = useRoute()
const router = useRouter()

const isRouteLoading = ref(false)
let removeBeforeGuard = null
let removeAfterGuard = null

const showNav = computed(() => route.name !== 'welcome')

const isMobileMenuOpen = ref(false)

const navLinks = [
  { name: 'main', label: '分析主页', path: '/main', icon: 'analysis' },
  { name: 'review', label: '智能阅卷', path: '/review', icon: 'review' },
  { name: 'knowledge', label: '知识库', path: '/knowledge', icon: 'knowledge' },
  { name: 'cases', label: '案件管理', path: '/cases', icon: 'cases' },
  { name: 'experiment', label: '实验采集', path: '/experiment', icon: 'experiment' },
  { name: 'settings', label: '系统管理', path: '/settings', icon: 'settings' },
]

function isActive(link) {
  return route.name === link.name
}

function handleNavigate(path) {
  isMobileMenuOpen.value = false
  router.push(path)
}

function toggleMobileMenu() {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

watch(route, () => {
  isMobileMenuOpen.value = false
})

onMounted(() => {
  removeBeforeGuard = router.beforeEach(() => {
    isRouteLoading.value = true
  })
  removeAfterGuard = router.afterEach(() => {
    isRouteLoading.value = false
  })
})

onUnmounted(() => {
  if (removeBeforeGuard) {
    removeBeforeGuard()
    removeBeforeGuard = null
  }
  if (removeAfterGuard) {
    removeAfterGuard()
    removeAfterGuard = null
  }
})
</script>

<template>
  <div class="app-container">
    <nav
      v-if="showNav"
      class="top-nav"
      role="navigation"
      aria-label="主导航"
    >
      <div class="nav-inner">
        <div
          class="nav-brand"
          @click="handleNavigate('/main')"
        >
          <span class="nav-logo">⚖️</span>
          <span class="nav-title">主观明知分析系统</span>
        </div>

        <!-- 桌面端导航链接 -->
        <div class="nav-links nav-links-desktop">
          <button
            v-for="link in navLinks"
            :key="link.name"
            class="nav-link"
            :class="{ active: isActive(link) }"
            @click="handleNavigate(link.path)"
          >
            {{ link.label }}
          </button>
        </div>

        <!-- 移动端汉堡菜单按钮 -->
        <button
          class="hamburger-btn"
          :class="{ 'hamburger-open': isMobileMenuOpen }"
          :aria-expanded="isMobileMenuOpen"
          :aria-label="isMobileMenuOpen ? '关闭导航菜单' : '打开导航菜单'"
          aria-controls="mobile-nav-menu"
          @click="toggleMobileMenu"
        >
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
          <span class="hamburger-line"></span>
        </button>
      </div>

      <!-- 移动端下拉菜单 -->
      <transition name="mobile-menu">
        <div
          v-show="isMobileMenuOpen"
          id="mobile-nav-menu"
          class="mobile-nav-menu"
          role="menu"
          :aria-hidden="!isMobileMenuOpen"
        >
          <button
            v-for="link in navLinks"
            :key="link.name"
            class="mobile-nav-link"
            :class="{ active: isActive(link) }"
            role="menuitem"
            @click="handleNavigate(link.path)"
          >
            {{ link.label }}
          </button>
        </div>
      </transition>
    </nav>
    <router-view v-slot="{ Component }">
      <transition
        name="fade"
        mode="out-in"
      >
        <component :is="Component" />
      </transition>
    </router-view>

    <!-- 路由加载状态指示器 -->
    <div v-show="isRouteLoading" class="route-loading">
      <div class="route-loading-spinner"></div>
      <span class="route-loading-text">页面加载中...</span>
    </div>

    <!-- 系统级固定水印：在所有页面持续可见，不被遮挡，pointer-events 设为 none 避免阻挡交互 -->
    <div
      class="system-watermark"
      role="note"
      aria-label="系统免责声明"
    >
      <span class="system-watermark-text">{{ SYSTEM_DISCLAIMER }}</span>
    </div>
  </div>
</template>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  /* 主题色 */
  --color-primary: #4f46e5;
  --color-primary-hover: #4338ca;
  --color-success: #22c55e;
  --color-warning: #eab308;
  --color-danger: #ef4444;
  --color-info: #3b82f6;

  /* 背景色 */
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-tertiary: #f1f5f9;

  /* 文本色 */
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-tertiary: #94a3b8;

  /* 边框 */
  --border-color: #e2e8f0;
  --border-radius: 8px;
  --border-radius-lg: 12px;

  /* 阴影 */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);

  /* 过渡 */
  --transition-fast: 150ms ease;
  --transition-normal: 300ms ease;
  --transition-slow: 500ms ease;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-primary);
  background-color: var(--bg-secondary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
.app-container {
  min-height: 100vh;
}

.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
}

.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 56px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
}

.nav-logo {
  font-size: 1.375rem;
}

.nav-title {
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
}

.nav-links {
  display: flex;
  gap: 0.25rem;
}

/* 桌面端始终显示导航链接 */
.nav-links-desktop {
  display: flex;
}

.nav-link {
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-secondary);
  background: none;
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.nav-link.active {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  font-weight: 600;
}

/* 汉堡菜单按钮 - 默认隐藏（桌面端） */
.hamburger-btn {
  display: none;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 5px;
  width: 44px;
  height: 44px;
  padding: 10px;
  background: none;
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background var(--transition-fast);
  -webkit-tap-highlight-color: transparent;
}

.hamburger-btn:hover {
  background: var(--bg-tertiary);
}

.hamburger-btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.hamburger-line {
  display: block;
  width: 22px;
  height: 2px;
  background: var(--text-primary);
  border-radius: 2px;
  transition: all 300ms ease-in-out;
  transform-origin: center;
}

.hamburger-open .hamburger-line:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}

.hamburger-open .hamburger-line:nth-child(2) {
  opacity: 0;
  transform: scaleX(0);
}

.hamburger-open .hamburger-line:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}

/* 移动端下拉菜单 */
.mobile-nav-menu {
  overflow: hidden;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-md);
  padding: 0.5rem 1rem;
}

.mobile-nav-link {
  display: block;
  width: 100%;
  min-height: 44px;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-secondary);
  background: none;
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
  -webkit-tap-highlight-color: transparent;
}

.mobile-nav-link + .mobile-nav-link {
  margin-top: 2px;
}

.mobile-nav-link:hover,
.mobile-nav-link:focus-visible {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.mobile-nav-link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.mobile-nav-link.active {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  font-weight: 600;
}

/* 响应式布局 */
@media (max-width: 767px) {
  .nav-inner {
    padding: 0 1rem;
  }

  .nav-title {
    font-size: 0.9375rem;
  }

  .nav-links-desktop {
    display: none;
  }

  .hamburger-btn {
    display: flex;
  }
}

@media (min-width: 768px) {
  .nav-inner {
    padding: 0 1.5rem;
  }

  .nav-links-desktop {
    display: flex;
  }

  .hamburger-btn {
    display: none;
  }

  .mobile-nav-menu {
    display: none;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-normal);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.mobile-menu-enter-active,
.mobile-menu-leave-active {
  transition: all 300ms ease-in-out;
}

.mobile-menu-enter-from,
.mobile-menu-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.route-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 1rem;
  z-index: 9999;
  backdrop-filter: blur(4px);
}

.route-loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--bg-tertiary);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.route-loading-text {
  font-size: 1rem;
  color: var(--text-secondary);
  font-weight: 500;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 响应式容器 */
.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

@media (min-width: 768px) {
  .container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .container {
    padding: 0 2rem;
  }
}

/* 通用按钮样式 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  font-weight: 500;
  line-height: 1;
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--color-primary-hover);
}

.btn-secondary {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--border-color);
}

.btn-success {
  background-color: var(--color-success);
  color: white;
}

.btn-danger {
  background-color: var(--color-danger);
  color: white;
}

.btn-lg {
  padding: 1rem 2rem;
  font-size: 1.125rem;
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

/* 卡片样式 */
.card {
  background: var(--bg-primary);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-md);
  padding: 1.5rem;
}

/* 加载动画 */
.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--bg-tertiary);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* 工具类 */
.text-center {
  text-align: center;
}

.text-secondary {
  color: var(--text-secondary);
}

.mt-4 {
  margin-top: 1rem;
}

.mb-4 {
  margin-bottom: 1rem;
}

/* 系统级免责声明水印：固定在屏幕底部居中，使用 pointer-events: none 确保不阻挡交互 */
.system-watermark {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9000;
  display: flex;
  justify-content: center;
  pointer-events: none;
  padding: 0.5rem 1rem;
  /* 使用渐变背景防止纯文字与下方内容融合，同时不阻挡可读性 */
  background: linear-gradient(
    to top,
    rgba(248, 250, 252, 0.95) 0%,
    rgba(248, 250, 252, 0.6) 60%,
    rgba(248, 250, 252, 0) 100%
  );
}

.system-watermark-text {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary, #64748b);
  letter-spacing: 0.02em;
  text-align: center;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 999px;
  user-select: none;
}
</style>
