<script setup>
defineOptions({ name: 'AppSidebar' })

const props = defineProps({
  menuItems: {
    type: Array,
    default: () => [],
  },
  currentRoute: {
    type: String,
    default: '',
  },
  isCollapsed: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['navigate'])

function isActive(item) {
  return props.currentRoute === item.name
}

function getMenuItemPath(item) {
  return item.path || '/'
}
</script>

<template>
  <aside
    class="app-sidebar"
    :class="{ 'sidebar-collapsed': isCollapsed }"
  >
    <nav class="sidebar-nav">
      <ul class="sidebar-menu">
        <li
          v-for="item in menuItems"
          :key="item.name"
        >
          <a
            :href="getMenuItemPath(item)"
            class="sidebar-link"
            :class="{ active: isActive(item) }"
            :title="item.label"
            @click.prevent="$emit('navigate', item)"
          >
            <span
              v-if="item.icon"
              class="sidebar-icon"
            >{{ item.icon }}</span>
            <span
              v-show="!isCollapsed"
              class="sidebar-label"
            >{{ item.label }}</span>
          </a>
        </li>
      </ul>
    </nav>
  </aside>
</template>

<style scoped>
.app-sidebar {
  width: 240px;
  min-height: calc(100vh - 56px);
  background: var(--bg-primary, #fff);
  border-right: 1px solid var(--border-color, #e2e8f0);
  transition: width var(--transition-normal, 300ms ease);
  overflow-x: hidden;
}

.sidebar-collapsed {
  width: 64px;
}

.sidebar-nav {
  padding: 1rem 0;
}

.sidebar-menu {
  list-style: none;
  margin: 0;
  padding: 0;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  color: var(--text-secondary, #64748b);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all var(--transition-fast, 150ms ease);
  white-space: nowrap;
  border-left: 3px solid transparent;
}

.sidebar-link:hover {
  color: var(--text-primary, #1e293b);
  background: var(--bg-tertiary, #f1f5f9);
}

.sidebar-link.active {
  color: var(--color-primary, #4f46e5);
  background: rgba(79, 70, 229, 0.06);
  border-left-color: var(--color-primary, #4f46e5);
}

.sidebar-icon {
  font-size: 1.125rem;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.sidebar-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-collapsed .sidebar-link {
  justify-content: center;
  padding: 0.75rem;
}

@media (max-width: 767px) {
  .app-sidebar {
    position: fixed;
    left: 0;
    top: 56px;
    z-index: 90;
    height: calc(100vh - 56px);
    transform: translateX(-100%);
    transition: transform var(--transition-normal, 300ms ease);
  }

  .sidebar-collapsed {
    width: 240px;
    transform: translateX(0);
  }
}
</style>