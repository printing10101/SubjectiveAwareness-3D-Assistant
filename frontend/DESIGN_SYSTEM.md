# 设计系统文档 (DESIGN_SYSTEM.md)

> 版本：1.0.0 | 最后更新：2026-06-15

本文档详细记录帮信罪辅助裁定软件前端的设计系统，包括设计令牌、组件规范、使用指南和代码示例。

---

## 目录

1. [设计令牌 (Design Tokens)](#1-设计令牌)
2. [布局系统](#2-布局系统)
3. [组件文档](#3-组件文档)
4. [动效系统](#4-动效系统)
5. [响应式设计](#5-响应式设计)
6. [无障碍设计](#6-无障碍设计)
7. [最佳实践](#7-最佳实践)

---

## 1. 设计令牌

设计令牌是设计系统的基础，定义在 `frontend/src/assets/styles/tokens.css`。

### 1.1 颜色系统

#### 背景色

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--color-bg-base` | `#F5F2EC` | 页面基底背景（米白色） |
| `--color-bg-secondary` | `#FAF8F4` | 次要背景区域 |
| `--color-bg-card` | `#FFFFFF` | 卡片、容器背景 |
| `--color-bg-glass` | `rgba(245, 242, 236, 0.85)` | 磨砂玻璃效果背景 |

#### 文字色

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--color-text-primary` | `#1D1D1F` | 主标题、正文 |
| `--color-text-secondary` | `#6E6E73` | 次要文字、说明 |
| `--color-text-tertiary` | `#AEAEB2` | 辅助文字、占位符 |

#### 边框色

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--color-border-subtle` | `#E8E3D9` | 弱边框（卡片、分割线） |
| `--color-border-strong` | `#D4CFC2` | 强边框（焦点、强调） |

#### 高光色

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--color-accent-copper` | `#8B6F47` | 古铜色主强调 |
| `--color-accent-gold` | `#B8956A` | 金色辅助强调 |

#### 语义色

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--color-success` | `#2D7D4A` | 成功状态 |
| `--color-warning` | `#B8791E` | 警告状态 |
| `--color-error` | `#B23A2A` | 错误状态 |

### 1.2 字体系统

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--font-sans` | `system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif` | 正文无衬线字体 |
| `--font-serif` | `'Source Han Serif SC', 'Songti SC', 'Noto Serif SC', serif` | 标题衬线字体 |
| `--font-mono` | `'JetBrains Mono', 'SF Mono', Consolas, monospace` | 代码等宽字体 |

#### 响应式字号

| 变量名 | 值 | 范围 | 用途 |
|--------|-----|------|------|
| `--text-display` | `clamp(2.5rem, 5vw, 4rem)` | 40–64px | 超大标题 |
| `--text-h1` | `clamp(1.75rem, 3vw, 2.5rem)` | 28–40px | 页面主标题 |
| `--text-h2` | `clamp(1.25rem, 2vw, 1.75rem)` | 20–28px | 章节标题 |
| `--text-h3` | `clamp(1rem, 1.5vw, 1.25rem)` | 16–20px | 小标题 |
| `--text-body` | `1rem` | 16px | 正文 |
| `--text-small` | `0.875rem` | 14px | 小号文字 |
| `--text-micro` | `0.75rem` | 12px | 辅助文字 |

### 1.3 间距系统

基于 4px 基础单位，提供 8 档间距：

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--spacing-1` | `4px` | 极小间距 |
| `--spacing-2` | `8px` | 小间距 |
| `--spacing-3` | `12px` | 中小间距 |
| `--spacing-4` | `16px` | 基础间距 |
| `--spacing-5` | `24px` | 中间距 |
| `--spacing-6` | `32px` | 中大间距 |
| `--spacing-7` | `48px` | 大间距 |
| `--spacing-8` | `64px` | 超大间距 |

### 1.4 圆角系统

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--radius-sm` | `6px` | 按钮、输入框、徽章 |
| `--radius-md` | `10px` | 卡片、容器 |
| `--radius-lg` | `16px` | 模态框、弹出层 |
| `--radius-xl` | `24px` | 特殊容器 |
| `--radius-full` | `9999px` | 圆形、胶囊形 |

### 1.5 阴影系统

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--shadow-1` | `0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03)` | 卡片默认阴影 |
| `--shadow-2` | `0 4px 12px rgba(0,0,0,0.05), 0 2px 6px rgba(0,0,0,0.03)` | 悬停状态 |
| `--shadow-3` | `0 8px 30px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)` | 弹出层 |
| `--shadow-4` | `0 16px 48px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.05)` | 模态框 |

### 1.6 动效系统

#### 缓动函数

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--ease-out` | `cubic-bezier(0.25, 0.1, 0.25, 1)` | 默认缓出（推荐） |
| `--ease-in` | `cubic-bezier(0.42, 0, 1, 1)` | 缓入 |
| `--ease-in-out` | `cubic-bezier(0.42, 0, 0.58, 1)` | 缓入缓出 |

#### 持续时间

| 变量名 | 值 | 用途 |
|--------|-----|------|
| `--duration-instant` | `100ms` | 即时反馈 |
| `--duration-fast` | `150ms` | 快速过渡 |
| `--duration-base` | `250ms` | 基础过渡 |
| `--duration-normal` | `300ms` | 常规过渡 |
| `--duration-slow` | `400ms` | 慢速过渡 |
| `--duration-number` | `600ms` | 数字滚动 |
| `--duration-skeleton` | `1.5s` | 骨架屏动画 |

#### 预设过渡

| 变量名 | 值 |
|--------|-----|
| `--transition-fast` | `var(--duration-fast) var(--ease-out)` |
| `--transition-base` | `var(--duration-base) var(--ease-out)` |
| `--transition-normal` | `var(--duration-normal) var(--ease-out)` |
| `--transition-slow` | `var(--duration-slow) var(--ease-out)` |

---

## 2. 布局系统

### 2.1 布局尺寸

| 变量名 | 桌面端 | 移动端 | 说明 |
|--------|--------|--------|------|
| `--layout-sidebar-width` | `240px` | `0px` | 侧边栏宽度 |
| `--layout-header-height` | `56px` | `48px` | 头部高度 |
| `--layout-tab-height` | `48px` | `44px` | 底部 Tab 高度 |
| `--layout-content-max-width` | `1200px` | `100%` | 内容最大宽度 |

### 2.2 布局结构

```
┌─────────────────────────────────────────┐
│              AppHeader (56px)           │
├──────────┬──────────────────────────────┤
│          │                              │
│ AppSidebar│      Main Content          │
│  (240px) │     (max-width: 1200px)      │
│          │                              │
├──────────┴──────────────────────────────┤
│          MobileTabbar (48px)            │
│         (仅 <768px 显示)                 │
└─────────────────────────────────────────┘
```

### 2.3 页面容器

```vue
<template>
  <PageContainer>
    <div class="content">
      <!-- 页面内容 -->
    </div>
  </PageContainer>
</template>
```

`PageContainer` 自动处理：
- 最大宽度限制（1200px）
- 水平居中
- 响应式内边距

---

## 3. 组件文档

### 3.1 BaseButton 基础按钮

**功能**：可点击的操作按钮

**属性 (Props)**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `variant` | `'primary' \| 'secondary' \| 'danger'` | `'primary'` | 按钮样式变体 |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | 按钮尺寸 |
| `disabled` | `boolean` | `false` | 是否禁用 |
| `loading` | `boolean` | `false` | 是否加载中 |

**事件 (Events)**

| 事件 | 参数 | 说明 |
|------|------|------|
| `click` | `MouseEvent` | 点击事件（disabled/loading 时不触发） |

**插槽 (Slots)**

| 插槽 | 说明 |
|------|------|
| `default` | 按钮内容 |
| `icon` | 按钮图标（左侧） |

**使用示例**

```vue
<template>
  <BaseButton variant="primary" @click="handleSubmit">
    提交
  </BaseButton>

  <BaseButton variant="secondary" size="sm">
    取消
  </BaseButton>

  <BaseButton :loading="isLoading" @click="save">
    保存
  </BaseButton>
</template>
```

### 3.2 BaseInput 输入框

**功能**：单行文本输入

**属性 (Props)**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `modelValue` | `string` | `''` | 绑定值 |
| `type` | `string` | `'text'` | 输入类型 |
| `placeholder` | `string` | `''` | 占位文本 |
| `disabled` | `boolean` | `false` | 是否禁用 |
| `error` | `string` | `''` | 错误提示文本 |

**事件 (Events)**

| 事件 | 参数 | 说明 |
|------|------|------|
| `update:modelValue` | `string` | 值变化 |
| `focus` | `FocusEvent` | 聚焦 |
| `blur` | `FocusEvent` | 失焦 |

**使用示例**

```vue
<template>
  <BaseInput
    v-model="username"
    placeholder="请输入用户名"
    :error="usernameError"
  />
</template>
```

### 3.3 BaseCard 卡片

**功能**：内容容器

**属性 (Props)**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `hoverable` | `boolean` | `false` | 是否支持悬停效果 |
| `padding` | `'sm' \| 'md' \| 'lg'` | `'md'` | 内边距大小 |

**插槽 (Slots)**

| 插槽 | 说明 |
|------|------|
| `default` | 卡片内容 |
| `header` | 卡片头部 |
| `footer` | 卡片底部 |

**使用示例**

```vue
<template>
  <BaseCard hoverable>
    <template #header>
      <h3>卡片标题</h3>
    </template>
    <p>卡片内容</p>
    <template #footer>
      <BaseButton size="sm">操作</BaseButton>
    </template>
  </BaseCard>
</template>
```

### 3.4 BaseModal 模态框

**功能**：弹出对话框

**属性 (Props)**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `modelValue` | `boolean` | `false` | 是否显示 |
| `title` | `string` | `''` | 标题 |
| `width` | `string` | `'500px'` | 宽度 |
| `closable` | `boolean` | `true` | 是否显示关闭按钮 |

**事件 (Events)**

| 事件 | 参数 | 说明 |
|------|------|------|
| `update:modelValue` | `boolean` | 显示状态变化 |
| `close` | - | 关闭事件 |

**使用示例**

```vue
<template>
  <BaseModal v-model="showModal" title="确认删除">
    <p>确定要删除这条记录吗？</p>
    <template #footer>
      <BaseButton variant="secondary" @click="showModal = false">取消</BaseButton>
      <BaseButton variant="danger" @click="confirmDelete">确认</BaseButton>
    </template>
  </BaseModal>
</template>
```

### 3.5 BaseDrawer 抽屉

**功能**：侧边滑出面板

**属性 (Props)**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `modelValue` | `boolean` | `false` | 是否显示 |
| `placement` | `'left' \| 'right' \| 'bottom'` | `'right'` | 弹出方向 |
| `width` | `string` | `'300px'` | 宽度（左右方向） |
| `height` | `string` | `'50vh'` | 高度（底部方向） |

**使用示例**

```vue
<template>
  <BaseDrawer v-model="showDrawer" placement="right" width="400px">
    <h3>详情</h3>
    <p>抽屉内容</p>
  </BaseDrawer>
</template>
```

### 3.6 BaseToast 提示

**功能**：轻量级消息提示

**属性 (Props)**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | `'success' \| 'error' \| 'warning' \| 'info'` | `'info'` | 提示类型 |
| `message` | `string` | `''` | 提示内容 |
| `duration` | `number` | `3000` | 显示时长（ms），0 为不自动关闭 |

**使用示例**

```vue
<script setup>
import { useToast } from '@/composables/useToast'

const toast = useToast()

function handleSuccess() {
  toast.success('操作成功')
}

function handleError() {
  toast.error('操作失败，请重试')
}
</script>
```

### 3.7 BaseTable 表格

**功能**：数据表格

**属性 (Props)**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `data` | `Array` | `[]` | 表格数据 |
| `columns` | `Array` | `[]` | 列配置 |
| `loading` | `boolean` | `false` | 是否加载中 |
| `pagination` | `object` | `null` | 分页配置 |

**使用示例**

```vue
<template>
  <BaseTable
    :data="tableData"
    :columns="columns"
    :loading="isLoading"
  />
</template>

<script setup>
const columns = [
  { key: 'name', title: '名称', width: '200px' },
  { key: 'status', title: '状态' },
  { key: 'actions', title: '操作', width: '150px' }
]
</script>
```

### 3.8 AnimatedNumber 数字动画

**功能**：数字滚动动画

**属性 (Props)**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `value` | `number` | `0` | 目标数值 |
| `duration` | `number` | `600` | 动画时长（ms） |
| `decimals` | `number` | `0` | 小数位数 |

**使用示例**

```vue
<template>
  <AnimatedNumber :value="score" :decimals="1" />
</template>
```

### 3.9 BaseSkeleton 骨架屏

**功能**：加载占位

**属性 (Props)**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `variant` | `'text' \| 'circle' \| 'rect'` | `'text'` | 形状 |
| `width` | `string` | `'100%'` | 宽度 |
| `height` | `string` | `'1em'` | 高度 |

**使用示例**

```vue
<template>
  <div v-if="loading">
    <BaseSkeleton width="200px" height="20px" />
    <BaseSkeleton width="100%" height="100px" variant="rect" />
  </div>
  <div v-else>
    <!-- 实际内容 -->
  </div>
</template>
```

---

## 4. 动效系统

动效定义在 `frontend/src/assets/styles/animations.css`。

### 4.1 页面过渡

```vue
<template>
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>
```

效果：淡入 + 上滑（250ms）

### 4.2 卡片悬停

```vue
<template>
  <BaseCard class="card-hover">
    悬停时上浮 2px + 阴影增强
  </BaseCard>
</template>
```

### 4.3 按钮交互

```vue
<template>
  <BaseButton class="btn-interactive">
    悬停上浮 1px + 颜色加深
  </BaseButton>
</template>
```

### 4.4 模态框过渡

```vue
<template>
  <transition name="modal">
    <BaseModal v-if="show">
      缩放 + 淡入（250ms）
    </BaseModal>
  </transition>
</template>
```

### 4.5 抽屉动画

```vue
<template>
  <transition name="drawer">
    <BaseDrawer v-if="show">
      滑入（300ms）
    </BaseDrawer>
  </transition>
</template>
```

### 4.6 Toast 动画

```vue
<transition name="toast">
  <BaseToast>
    上滑淡入（250ms）
  </BaseToast>
</transition>
```

### 4.7 骨架屏动画

```vue
<template>
  <div class="skeleton-shimmer" style="width: 200px; height: 20px;">
    扫描式渐变动画（1.5s 循环）
  </div>
</template>
```

---

## 5. 响应式设计

### 5.1 断点定义

| 断点名 | 范围 | 布局策略 |
|--------|------|----------|
| 移动端 | `<768px` | 单列，底部 Tab，侧边栏隐藏 |
| 平板端 | `768px–1279px` | 双列，侧边栏折叠（60px） |
| 桌面端 | `≥1280px` | 三列，侧边栏展开（240px） |

### 5.2 响应式工具类

```css
/* 移动端隐藏 */
.desktop-hide { /* <768px 时 display: none */ }

/* 桌面端隐藏 */
.mobile-hide { /* ≥769px 时 display: none */ }
```

**使用示例**

```vue
<template>
  <div class="desktop-hide">
    仅在移动端显示
  </div>
  <div class="mobile-hide">
    仅在桌面端显示
  </div>
</template>
```

### 5.3 响应式字号

使用 `clamp()` 实现流式字号，自动适配视口：

```css
h1 {
  font-size: var(--text-h1); /* clamp(1.75rem, 3vw, 2.5rem) */
}
```

### 5.4 响应式间距

```css
@media (max-width: 768px) {
  :root {
    --spacing-page-padding: var(--spacing-4); /* 16px */
  }
}

@media (min-width: 769px) {
  :root {
    --spacing-page-padding: var(--spacing-6); /* 32px */
  }
}
```

---

## 6. 无障碍设计

### 6.1 焦点环

所有可交互元素均支持 `:focus-visible` 焦点环：

```css
:focus-visible {
  outline: 3px solid rgba(139, 111, 71, 0.4);
  outline-offset: 2px;
}
```

### 6.2 Skip to Main

为键盘用户提供快速跳转：

```vue
<template>
  <a href="#main" class="skip-to-main">跳转到主内容</a>
  <AppLayout>
    <main id="main">
      <!-- 主内容 -->
    </main>
  </AppLayout>
</template>
```

### 6.3 减少动效

尊重用户的系统设置：

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 6.4 高对比度模式

```css
@media (forced-colors: active) {
  :focus-visible {
    outline: 3px solid LinkText;
  }
}
```

---

## 7. 最佳实践

### 7.1 样式组织

```vue
<style scoped>
/* 1. 布局相关 */
.container { ... }

/* 2. 组件样式 */
.card { ... }

/* 3. 状态样式 */
.is-loading { ... }

/* 4. 响应式覆盖 */
@media (max-width: 768px) { ... }
</style>
```

### 7.2 使用设计令牌

```css
/* 推荐：使用令牌 */
.card {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-2);
  padding: var(--spacing-5);
}

/* 不推荐：硬编码值 */
.card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  padding: 24px;
}
```

### 7.3 工具类优先

对于简单的样式，优先使用工具类：

```vue
<!-- 推荐 -->
<div class="p-4 mb-4 text-center">

<!-- 不推荐 -->
<div style="padding: 16px; margin-bottom: 16px; text-align: center;">
```

### 7.4 组件组合

```vue
<template>
  <PageContainer>
    <BaseCard class="mb-6">
      <template #header>
        <h2 class="text-h2 text-primary">标题</h2>
      </template>
      
      <BaseInput v-model="query" placeholder="搜索..." class="mb-4" />
      
      <BaseTable :data="results" :columns="columns" />
      
      <template #footer>
        <BasePagination :total="100" :current="page" />
      </template>
    </BaseCard>
  </PageContainer>
</template>
```

### 7.5 动效使用

```vue
<template>
  <!-- 页面过渡 -->
  <transition name="page" mode="out-in">
    <router-view />
  </transition>

  <!-- 列表过渡 -->
  <transition-group name="fade" tag="div">
    <BaseCard v-for="item in items" :key="item.id">
      {{ item.name }}
    </BaseCard>
  </transition-group>
</template>
```

---

## 附录

### A. 文件结构

```
frontend/src/assets/styles/
├── tokens.css       # 设计令牌（颜色、间距、圆角、阴影、动效变量）
├── base.css         # 基础重置 + 全局样式
├── utilities.css    # 工具类（间距、文字、背景等）
├── animations.css   # 动效系统（过渡、关键帧）
├── variables.css    # 旧变量（过渡期兼容）
└── global.css       # 全局样式（焦点环、无障碍）
```

### B. 浏览器兼容性

| 特性 | Chrome | Firefox | Safari | Edge |
|------|--------|---------|--------|------|
| CSS Variables | 49+ | 31+ | 9.1+ | 15+ |
| clamp() | 79+ | 75+ | 13.1+ | 79+ |
| aspect-ratio | 88+ | 89+ | 15+ | 88+ |
| :focus-visible | 86+ | 85+ | 15.4+ | 86+ |

### C. 相关文档

- [README.md](../README.md) - 项目概览
- [CHANGELOG.md](../CHANGELOG.md) - 变更日志
- [综合技术文档](../docs/综合技术文档.md) - 完整技术文档

---

> 本文档随项目迭代持续更新。如有疑问或建议，请提交 Issue 或 Pull Request。
