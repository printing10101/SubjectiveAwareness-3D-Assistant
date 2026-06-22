# components/common/ 目录说明

## V1.0 版本设计历史

### 原设计意图

在 V1.0 版本初期，`components/common/` 目录被设计为存放全局通用 UI 组件的公共区域，旨在提供可复用的基础组件，供整个前端应用的不同模块调用。该目录与 `components/layout/` 目录并行存在，分别承担不同的职责：

- **common/**：存放业务无关的通用展示组件（如加载指示器、卡片组件等）
- **layout/**：存放页面布局框架组件（如页头、侧边栏、页面容器等）

### 主要组件功能

在 V1.0 早期版本中，本目录曾包含以下组件：

| 组件名称 | 功能描述 | 状态 |
|---------|---------|------|
| `AppHeader.vue` | 顶栏导航组件，提供全局导航功能 | 已迁移至 `components/layout/` |
| `AppSidebar.vue` | 侧边栏导航组件，提供菜单导航功能 | 已迁移至 `components/layout/` |
| `LoadingSpinner.vue` | 全局加载旋转指示器，用于异步操作反馈 | 已移除（无引用） |
| `CaseCard.vue` | 案件卡片组件，用于案件列表展示 | 未实际创建 |
| `KnowledgeGraph.vue` | 知识图谱可视化组件 | 未实际创建 |

### 本次清理原因

在 V1.0 版本开发过程中，项目架构经历了以下演进：

1. **布局组件重新组织**：`AppHeader.vue` 和 `AppSidebar.vue` 被重新定位为页面布局框架的核心组件，因此迁移至 `components/layout/` 目录，与 `AppLayout.vue`、`MobileTabbar.vue`、`PageContainer.vue` 共同构成完整的布局系统。

2. **组件引用检查**：通过全局代码引用扫描，确认 `LoadingSpinner.vue` 等组件在项目中完全无引用，属于孤儿组件。

3. **目录职责明确化**：为避免组件存放混乱，决定清空 `components/common/` 目录，将所有通用组件统一归口管理。未来如需新增通用组件，建议直接放置在 `components/ui/` 或功能模块目录下。

### 当前状态

本目录现已清空，保留此 README.md 文件以记录 V1.0 版本的设计演进历史。

---

**文档版本**：V1.0.0  
**最后更新**：2026-06-18
