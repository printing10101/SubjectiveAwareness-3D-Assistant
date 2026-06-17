# 前端系统分析报告

> 生成日期：2026-06-14  
> 项目版本：V1.0.0  
> 分析目标：建立完整功能基线，为后续重构提供基准依据

---

## 1. 项目概览

| 项目 | 内容 |
|------|------|
| 框架 | Vue 3.4 + Vite 5 |
| 路由 | Vue Router 4 |
| 状态管理 | Pinia 2 |
| HTTP 客户端 | Axios 1.6 |
| UI 库 | Element Plus 2.9（仅 LabelingView 使用） |
| Markdown 编辑器 | md-editor-v3 |
| Markdown 解析 | marked |
| 图表 | D3.js 7 |
| 错误追踪 | Sentry Vue 8 |
| PDF 生成 | jsPDF 4 + html2canvas |
| 测试 | Vitest 4 + Vue Test Utils 2 |
| E2E 测试 | Cypress 13 |
| 代码规范 | ESLint + Prettier |

---

## 2. 依赖分析

### 2.1 生产依赖

| 包名 | 版本 | 主要用途 |
|------|------|----------|
| `@sentry/vue` | ^8.40.0 | 前端错误追踪与性能监控 |
| `axios` | ^1.6.7 | HTTP 请求客户端 |
| `d3` | ^7.9.0 | 知识图谱可视化（力导向图） |
| `element-plus` | ^2.9.10 | 部分页面 UI 组件（LabelingView） |
| `file-saver` | ^2.0.5 | 文件下载辅助 |
| `html2canvas` | ^1.4.1 | HTML 截图转 Canvas |
| `jspdf` | ^4.2.1 | PDF 生成 |
| `marked` | ^18.0.4 | Markdown 渲染 |
| `md-editor-v3` | ^6.5.1 | Markdown 编辑器组件 |
| `pinia` | ^2.1.7 | 状态管理 |
| `vue` | ^3.4.0 | 前端框架 |
| `vue-router` | ^4.3.0 | 路由管理 |

### 2.2 开发依赖

| 包名 | 版本 | 主要用途 |
|------|------|----------|
| `@vitejs/plugin-vue` | ^5.0.4 | Vite Vue 插件 |
| `@vitest/coverage-v8` | ^4.1.7 | 测试覆盖率 |
| `@vue/test-utils` | ^2.4.10 | Vue 组件测试工具 |
| `cypress` | ^13.17.0 | E2E 测试框架 |
| `eslint` | ^8.56.0 | 代码检查 |
| `eslint-config-prettier` | ^10.1.8 | Prettier 兼容配置 |
| `eslint-import-resolver-alias` | ^1.1.2 | Import 别名解析 |
| `eslint-plugin-import` | ^2.32.0 | Import 排序规则 |
| `eslint-plugin-unused-imports` | ^4.4.1 | 未使用导入检测 |
| `eslint-plugin-vue` | ^9.21.1 | Vue 语法检查 |
| `jsdom` | ^29.1.1 | 测试环境 DOM 模拟 |
| `prettier` | ^3.2.5 | 代码格式化 |
| `vite` | ^5.2.0 | 构建工具 |
| `vitest` | ^4.1.7 | 单元测试框架 |

---

## 3. 应用初始化流程

入口文件：`src/main.js`

1. **导入 Sentry**：条件初始化（需 `VITE_SENTRY_DSN` 环境变量）
2. **创建 Vue 实例**：`createApp(App)`
3. **初始化 Pinia**：`createPinia()`
4. **Sentry 集成**：`browserTracingIntegration` + `replayIntegration`
5. **Axios 全局配置**：baseURL='', timeout=30000ms, Content-Type=application/json
6. **Axios 请求拦截器**：自动附加 Bearer Token、请求计时
7. **Axios 响应拦截器**：
   - 401 → Token 刷新或跳转登录
   - 403 → 跳转禁止页面
   - 413/429 → 重试逻辑（最多 2 次）
   - 5xx → Sentry 上报
8. **注册全局插件**：errorPlugin（全局错误处理）
9. **注册 Pinia + Router**：`app.use(pinia)` + `app.use(router)`
10. **挂载**：`app.mount('#app')`

---

## 4. 根组件结构

`src/App.vue`

- **顶级容器**：`.app-container`
- **顶部导航**（条件渲染：非 welcome 页面）：主导航栏含品牌标识、6 个导航链接
- **路由出口**：`<router-view>` + fade 过渡动画
- **路由加载状态**：全屏遮罩 + 加载指示器
- **系统水印**：固定底部居中免责声明 "本系统为辅助参考工具，不构成法律意见。所有结论须经人工审查。"

### 导航链接配置

| 名称 | 标签 | 路径 |
|------|------|------|
| main | 分析主页 | /main |
| review | 智能阅卷 | /review |
| knowledge | 知识库 | /knowledge |
| cases | 案件管理 | /cases |
| experiment | 实验采集 | /experiment |
| settings | 系统管理 | /settings |

---

## 5. 路由系统

配置文件：`src/router/index.js`

### 路由守卫流程

1. **Sentry 面包屑**：记录每次导航
2. **协议验证**：未接受协议 → 跳转 `/agreement`
3. **登录验证**（`requiresAuth`）：未登录 → 跳转 `/login`
4. **管理员验证**（`requiresAdmin`）：非管理员 → `/403`
5. **知识库访问验证**（`requiresKnowledgeAccess`）：同 requiresAuth
6. **分析结果验证**（`requiresAnalysis`）：无结果 → `/generate`
7. **访客页面**（`guestOnly`）：已登录 → `/main`

### 完整路由表

| 路由路径 | 路由名称 | 页面组件 | 路由元信息 |
|----------|----------|----------|------------|
| `/` | welcome | WelcomeView | — |
| `/login` | login | LoginView | `guestOnly: true` |
| `/403` | forbidden | ForbiddenView | — |
| `/agreement` | agreement | AgreementView | `requiresAgreement: false, isAgreementPage: true` |
| `/generate` | generate | GenerateView | — |
| `/dashboard` | dashboard | DashboardView | `requiresAuth: true` |
| `/main` | main | MainView | — |
| `/report` | report | ReportView | `requiresAuth: true, requiresAnalysis: true` |
| `/cases` | cases | CasesView | `requiresAuth: true` |
| `/cases/:id` | caseDetail | CaseDetailView | `requiresAuth: true` |
| `/review` | review | ReviewView | `requiresAuth: true` |
| `/settings` | settings | SettingsView | `requiresAuth: true` |
| `/experiment` | experiment | ExperimentView | `requiresAuth: true, requiresAdmin: true` |
| `/knowledge` | knowledge | KnowledgeView | `requiresKnowledgeAccess: true` |
| `/knowledge/new` | knowledgeNew | KnowledgeEditView | `requiresAuth: true` |
| `/knowledge/:id` | knowledgeDetail | KnowledgeDetailView | `requiresKnowledgeAccess: true` |
| `/knowledge/:id/edit` | knowledgeEdit | KnowledgeEditView | `requiresAuth: true` |
| `/knowledge-graph` | knowledgeGraph | KnowledgeGraphView | `requiresKnowledgeAccess: true` |
| `/analysis` | analysis | AnalysisView | `requiresAuth: true` |
| `/analysis/:id` | analysisResult | AnalysisView | `requiresAuth: true` |
| `/upload` | upload | UploadView | `requiresAuth: true` |
| `/similar` | similar | SimilarCasesView | `requiresAuth: true` |
| `/eval` | eval | EvalCenterView | `requiresAuth: true, requiresAdmin: true` |
| `/labeling` | labeling | LabelingView | `requiresAuth: true, requiresAdmin: true` |
| `/:pathMatch(.*)*` | — | 重定向到 `/` | — |

---

## 6. 页面组件功能说明

### 6.1 WelcomeView (`/`)
**欢迎首页**：展示系统品牌、4 大核心功能卡片（分析新案件、历史分析、法律知识库、相似案例检索）、系统特色介绍及使用提示。首次访问显示"开始使用"按钮，非首次自动跳转 `/main`。

### 6.2 LoginView (`/login`)
**登录页面**：提供用户名/密码表单，调用 `POST /api/login` 进行认证，成功后存储 access_token 并跳转重定向目标页。

### 6.3 ForbiddenView (`/403`)
**无权限页面**：显示 403 禁止访问提示，列出可能原因（未登录/权限不足/资源受限），提供"返回首页"和"联系管理员"链接。

### 6.4 AgreementView (`/agreement`)
**用户协议页面**：展示完整用户协议（六大章节），需滚动到底部并勾选复选框后方可接受，接受后跳转回原请求路径。

### 6.5 GenerateView (`/generate`)
**分析结果生成提示页**：当用户尝试访问报告但无分析数据时显示，引导用户前往主界面执行分析。

### 6.6 DashboardView (`/dashboard`)
**仪表盘页面**：展示 4 个统计卡片（案件总数/待分析/已完成/近期分析）、"新建分析"和"查看所有案件"快捷按钮、近期案件列表（支持点击跳转详情）。

### 6.7 MainView (`/main`)
**分析主页面**：核心功能页。左栏为案件事实文本输入区 + Demo 案例快速体验按钮 + "开始分析"按钮；右栏显示分析状态提示/加载动画。支持缓存检测（避免重复 Token 消耗），分析完成后自动跳转报告页。

### 6.8 ReportView (`/report`)
**分析报告页面**：显示完整的多维度分析报告（11 个章节），包含左侧目录导航、分析维度矩阵可视化、人工审查清单（全选/保存/进度），支持 PDF 和 DOCX 格式下载。章节包括：基本信息、事实摘要、维度分析、触发规则、事实标签、冲突结果、相似案例、量刑建议、法律依据、审查结论、附录说明。

### 6.9 CasesView (`/cases`)
**案件管理页面**：案件列表（支持搜索、状态筛选、分页），提供"新建案件"对话框（名称+事实文本），每行支持查看详情和删除操作。

### 6.10 CaseDetailView (`/cases/:id`)
**案件详情页面**：展示案件基本信息（名称、状态、创建时间），支持执行分析、查看分析结果、编辑、删除操作，显示案件事实文本和分析结果摘要。

### 6.11 ReviewView (`/review`)
**智能阅卷页面**：上传案件文档（拖放/点击，支持 PDF/DOCX/DOC），自动提取文本内容到富文本编辑器，支持信息抽取（实体+关系），编辑后直接进入分析流程。

### 6.12 AnalysisView (`/analysis`) / (`/analysis/:id`)
**法律案件分析页面**：输入案件文本（至少10字符），调用分析 API，展示分析结果、维度矩阵和规则透明度面板。

### 6.13 UploadView (`/upload`)
**上传案件文件页面**：拖放/点击上传 .doc/.pdf/.txt 文件，显示上传进度和解析结果（案件基本信息、事实描述、关键证据、嫌疑人信息），支持编辑后保存分析。

### 6.14 SimilarCasesView (`/similar`)
**相似案例检索页面**：输入案情描述，调用 `POST /api/cases/similar` 检索相似历史案例，展示相似度评分、档级信息、判决结果和量刑信息。

### 6.15 KnowledgeView (`/knowledge`)
**知识库浏览页面**：左侧分类树导航（法律条文/分析方法/历史案例三级结构）+ 标签筛选，右侧卡片/列表双视图切换，支持搜索、排序、分页。提供"新建知识"入口。

### 6.16 KnowledgeDetailView (`/knowledge/:id`)
**知识详情页面**：展示知识条目完整信息（标题、分类、状态、信心评分、创建/更新时间、正文 Markdown 渲染、标签云），关联条目推荐，支持编辑和删除。

### 6.17 KnowledgeEditView (`/knowledge/new`) / (`/knowledge/:id/edit`)
**知识编辑页面**：新建/编辑知识条目表单，包含标题、分类、状态、信心评分、标签（自动补全）、Markdown 正文（使用 md-editor-v3），支持全屏预览。

### 6.18 KnowledgeGraphView (`/knowledge-graph`)
**知识图谱页面**：基于 D3.js 的力导向图可视化，左侧筛选面板（分类/标签/关系类型/搜索），支持节点交互点击跳转详情，显示关系图例。

### 6.19 SettingsView (`/settings`)
**系统管理页面**：左侧标签页导航（法律规则配置/模型版本信息/系统日志/用户管理）。规则配置支持 CRUD，模型信息展示评估指标环形图，日志支持级别筛选和搜索，用户管理支持增/禁/重置密码。

### 6.20 ExperimentView (`/experiment`)
**实验数据采集页面**：受控实验环境，A/B 组分别决定是否显示 AI 分析报告。包含案例展示、计时器、主观明知二选认定、置信度评分滑块、判断依据填写、AI 建议采纳记录（B组），提交后显示完成状态。

### 6.21 EvalCenterView (`/eval`)
**评测中心页面**：运行系统评测（消融实验/竞品对标），显示评测进度、结果表格（排序、变化标注）、CSV/PDF 导出，评测元信息。

### 6.22 LabelingView (`/labeling`)
**案件标注页面**（使用 Element Plus）：表格展示案件列表，每行可编辑 4 类标签（维度分档/最终定性/认定子类/司法时期），支持单行保存、批量标注、统计条、详情抽屉。

---

## 7. 组件清单

### 7.1 业务组件

| 组件名 | 文件路径 | 功能说明 |
|--------|----------|----------|
| AnalysisResult | `src/components/analysis/AnalysisResult.vue` | 分析结果展示组件 |
| DimensionMatrix | `src/components/analysis/DimensionMatrix.vue` | 分析维度矩阵可视化 |
| RuleTransparency | `src/components/analysis/RuleTransparency.vue` | 规则透明度面板 |
| CaseCard | `src/components/cases/CaseCard.vue` | 案件卡片组件 |
| KnowledgeGraph | `src/components/KnowledgeGraph.vue` | D3.js 知识图谱力导向图 |

### 7.2 通用组件

| 组件名 | 文件路径 | 功能说明 |
|--------|----------|----------|
| AppHeader | `src/components/common/AppHeader.vue` | 顶栏导航组件 |
| AppSidebar | `src/components/common/AppSidebar.vue` | 侧边栏导航组件 |
| LoadingSpinner | `src/components/common/LoadingSpinner.vue` | 加载动画指示器 |

---

## 8. Pinia Store 分析

### 8.1 useAnalysisStore (`stores/analysisStore.js`)

| 属性/方法 | 类型 | 初始值 | 说明 |
|-----------|------|--------|------|
| currentCaseText | State | '' | 当前案件文本内容 |
| analysisResult | State | null | 分析结果对象 |
| isLoading | State | false | 分析加载状态 |
| currentView | State | 'welcome' | 当前视图状态（持久化） |
| error | State | null | 错误信息 |
| cacheHit | State | null | 缓存命中标记 |
| responseTime | State | null | API 响应时间(ms) |
| tokensEstimate | State | null | Token 消耗估算 |
| hasCaseText | Getter | — | 是否有文本内容 |
| cacheSize | Getter | — | 内存缓存条目数 |
| setCaseText(text) | Action | — | 设置案件文本 |
| setAnalysisResult(result) | Action | — | 设置分析结果 |
| setView(view) | Action | — | 设置视图状态 |
| setLoading(loading) | Action | — | 设置加载状态 |
| setError(err) | Action | — | 设置错误 |
| clearError() | Action | — | 清除错误 |
| navigateToReport() | Action | — | 跳转报告页面 |
| navigateToMain() | Action | — | 跳转主页 |
| clearAnalysis() | Action | — | 清除分析结果 |
| reset() | Action | — | 重置所有状态 |
| generateCacheKey(text) | Action | — | 生成缓存键 |
| getCachedResult(key) | Action | — | 获取缓存结果 |
| setCachedResult(key, result) | Action | — | 设置缓存结果 |
| clearCache() | Action | — | 清空缓存（最大50条） |

**持久化**：currentCaseText、analysisResult、currentView 持久化到 localStorage。

### 8.2 useAuthStore (`stores/auth.js`)

| 属性/方法 | 类型 | 初始值 | 说明 |
|-----------|------|--------|------|
| userInfo | State | null | 当前用户信息（持久化） |
| isAuthLoading | State | false | 认证加载状态 |
| authError | State | null | 认证错误信息 |
| isLoggedIn | Getter | — | 是否已登录 |
| userRole | Getter | — | 用户角色 |
| isAdminUser | Getter | — | 是否为管理员 |
| displayName | Getter | — | 显示名称 |
| setUserInfo(info) | Action | — | 设置用户信息 |
| handleLoginSuccess(token, refresh, info) | Action | — | 登录成功处理 |
| handleLogout(router) | Action | — | 登出处理 |

**依赖**：`utils/auth.js`（JWT 解析、token 管理）、`utils/storage.js`

### 8.3 useCaseStore (`stores/case.js`)

| 属性/方法 | 类型 | 初始值 | 说明 |
|-----------|------|--------|------|
| caseList | State | [] | 案件列表 |
| currentCase | State | null | 当前选中案件 |
| totalCases | State | 0 | 案件总数 |
| currentPage | State | 1 | 当前页 |
| pageSize | State | 10 | 每页数 |
| isCaseLoading | State | false | 加载状态 |
| caseError | State | null | 错误信息 |
| searchKeyword | State | '' | 搜索关键词 |
| filterStatus | State | '' | 状态筛选 |
| hasCases | Getter | — | 是否有案件数据 |
| totalPages | Getter | — | 总页数 |
| hasNextPage | Getter | — | 是否有下一页 |
| hasPrevPage | Getter | — | 是否有上一页 |
| setCaseList(cases, total) | Action | — | 设置案件列表 |
| setCurrentCase(data) | Action | — | 设置当前案件 |
| addCase(newCase) | Action | — | 添加案件 |
| updateCase(updated) | Action | — | 更新案件 |
| removeCase(id) | Action | — | 删除案件 |
| reset() | Action | — | 重置 |

### 8.4 useKnowledgeStore (`stores/knowledgeStore.js`)

| 属性/方法 | 类型 | 初始值 | 说明 |
|-----------|------|--------|------|
| entries | State | [] | 知识条目列表 |
| currentEntry | State | null | 当前知识条目 |
| tags | State | [] | 可用标签列表 |
| total | State | 0 | 条目总数 |
| loading | State | false | 加载状态 |
| error | State | null | 错误信息 |
| fetchEntries(params) | Action | — | GET /api/knowledge |
| fetchEntry(id) | Action | — | GET /api/knowledge/:id |
| createEntry(data) | Action | — | POST /api/knowledge |
| updateEntry(id, data) | Action | — | PUT /api/knowledge/:id |
| deleteEntry(id) | Action | — | DELETE /api/knowledge/:id |
| fetchTags() | Action | — | GET /api/knowledge/tags |
| reset() | Action | — | 重置 |

**依赖**：`api/client.js`

---

## 9. API 层分析

### 9.1 API Client (`api/client.js`)
基于 Axios 封装的客户端，支持自动 Attach Token、401 自动刷新 Token、统一错误格式化。

### 9.2 认证 API (`api/auth.js`)

| 函数 | 方法 | 端点 | 参数 |
|------|------|------|------|
| login | POST | /api/auth/login | username, password |
| logout | POST | /api/auth/logout | — |
| refreshToken | POST | /api/auth/refresh | refresh_token |
| getCurrentUser | GET | /api/auth/me | — |

### 9.3 案件 API (`api/cases.js`)

| 函数 | 方法 | 端点 | 参数 |
|------|------|------|------|
| fetchCases | GET | /api/cases | params |
| fetchCaseById | GET | /api/cases/:id | — |
| createCase | POST | /api/cases | caseData |
| updateCase | PUT | /api/cases/:id | caseData |
| deleteCase | DELETE | /api/cases/:id | — |
| fetchCaseAnalysis | GET | /api/cases/:id/analysis | — |

### 9.4 分析 API (`api/analysis.js`)

| 函数 | 方法 | 端点 | 参数 |
|------|------|------|------|
| runAnalysis | POST | /api/analyze | case_text, options |
| fetchAnalysisResult | GET | /api/analyze/:id | — |
| fetchAnalysisHistory | GET | /api/analyze/history | params |
| fetchKnowledgeEntries | GET | /api/knowledge/entries | params |
| fetchKnowledgeEntryById | GET | /api/knowledge/entries/:id | — |

### 9.5 页面级其他 API 调用（直接使用 axios）

| 用途 | 方法 | 端点 |
|------|------|------|
| 登录 | POST | /api/login |
| 获取当前用户 | GET | /api/me |
| 仪表盘统计 | GET | /api/dashboard/stats |
| 文件上传解析 | POST | /api/extract |
| 实体抽取 | POST | /api/extract_entities |
| 分析提交 | POST | /api/analyze |
| 报告生成 | POST | /api/reports/generate |
| 报告详情 | GET | /api/reports/:id |
| 报告 PDF | GET | /api/reports/:id/pdf |
| 报告 DOCX | GET | /api/reports/:id/docx |
| 保存审查 | POST | /api/reports/:id/review |
| 相似案例 | POST | /api/cases/similar |
| 缓存统计 | GET | /api/cache/stats |
| 评测运行 | POST | /api/eval/run |
| 最新评测 | GET | /api/eval/latest |
| 实验进度 | GET | /api/experiment/progress |
| 分配案例 | GET | /api/experiment/assign-case |
| 提交判断 | POST | /api/experiment/submit-judgment |
| 法律规则 CRUD | GET/POST/PUT/DELETE | /api/rules[/:id] |
| 模型版本 | GET | /api/model-version |
| 系统日志 | GET | /api/logs |
| 用户管理 CRUD | GET/POST/PUT | /api/users[/:id] |
| 重置密码 | POST | /api/users/:id/reset-password |
| 知识图谱 | GET | /api/knowledge/graph |
| 案件标注 | GET/POST/DELETE | /api/cases/:id/labels |

---

## 10. 样式方案分析

### 10.1 主要样式方案：纯 CSS（CSS Custom Properties）

- **不使用 Tailwind CSS、SCSS 或其他 CSS 预处理器**
- 全部使用原生的 CSS + CSS 变量（Custom Properties）
- 变量定义在 `variables.css` 中，在 `main.js` 中全局导入

### 10.2 样式文件结构

| 文件 | 作用 |
|------|------|
| `src/assets/styles/variables.css` | CSS 变量定义（28个变量）：主题色、背景色、文本色、边框、阴影、过渡 |
| `src/assets/styles/global.css` | 全局样式重置 + 通用工具类（container, btn, card, loading-spinner, text-center 等） |
| 各 `.vue` 组件 `<style scoped>` | 组件级样式（scoped，不影响全局） |

### 10.3 样式方案特点

- **CSS 变量** 统一管理，通过 `:root` 定义，在全局和组件内均可用
- **全局样式** 定义基础布局和通用组件类（按钮、卡片、加载动画）
- **组件样式** 全部使用 `scoped` 隔离，避免样式冲突
- **响应式** 各页面均包含 `@media` 响应式断点（768px、1024px 为主）
- **Font** 系统字体栈，无需额外字体文件
- **无样式混用**：所有页面统一使用纯 CSS，无多种方案混用情况

### 10.4 CSS 变量清单

```
--color-primary: #4f46e5      --color-primary-hover: #4338ca
--color-success: #22c55e      --color-warning: #eab308
--color-danger: #ef4444       --color-info: #3b82f6
--bg-primary: #ffffff          --bg-secondary: #f8fafc
--bg-tertiary: #f1f5f9
--text-primary: #1e293b       --text-secondary: #64748b
--text-tertiary: #94a3b8
--border-color: #e2e8f0       --border-radius: 8px
--border-radius-lg: 12px
--shadow-sm/md/lg             --transition-fast/normal/slow
```

---

## 11. 基线测试结果

### 11.1 构建测试 (`npm run build`)

| 指标 | 数值 |
|------|------|
| 构建状态 | ✅ 成功 |
| 开始时间 | — |
| 结束时间 | — |
| 总耗时 | 1m 19s |
| 产物总大小 | 约 2.34 MB 未压缩 |
| 最大 chunk | KnowledgeEditView: 873.19 KB (gzip: 303.47 KB) |
| 警告 | 2 个 `__PURE__` 注释警告（@vueuse/core）|
| 警告 | 1 个 chunk 大小 >500KB 提示 |

### 11.2 Lint 检查 (`npm run lint`)

| 指标 | 数值 |
|------|------|
| 总状态 | ❌ 有错误 |
| 错误总数 | **25** |
| 警告总数 | **14** |
| 自动可修复 | 24 错误 + 4 警告 |

#### 错误分类

| 错误类型 | 数量 | 主要位置 |
|----------|------|----------|
| `vue/html-self-closing` | 7 | RuleTransparency, ReportView, LabelingView, UploadView |
| `import/order` | 4 | main.js(2), EvalCenterView, LabelingView, SimilarCasesView |
| `vue/max-attributes-per-line` | 3 | LabelingView |
| `no-undef` (Sentry) | 1 | router/index.js |
| `prefer-template` | 2 | LabelingView, UploadView |
| `arrow-body-style` | 1 | ReportView |
| `object-shorthand` | 1 | ReportView |
| `vue/html-self-closing` (span) | 5 | LabelingView |

#### 警告分类

| 警告类型 | 数量 | 主要位置 |
|----------|------|----------|
| `unused-imports/no-unused-vars` | 10 | DimensionMatrix(2), ReportView(7), LabelingView(1) |
| `vue/attributes-order` | 4 | LabelingView |

### 11.3 单元测试 (`npm run test`)

| 指标 | 数值 |
|------|------|
| 测试状态 | ✅ 全部通过 |
| 测试文件数 | 1 (`tests/unit/WelcomeView.spec.js`) |
| 测试用例 | 6 |
| 通过数 | 6 |
| 失败数 | 0 |
| 跳过数 | 0 |
| 通过率 | 100% |
| 总耗时 | 7.20s |

#### 测试用例详情

1. ✅ renders the welcome title correctly
2. ✅ renders the subtitle
3. ✅ renders the start button
4. ✅ renders all four feature items
5. ✅ sets localStorage and navigates on start button click
6. ✅ navigates to /main on mount if already visited

---

## 12. 功能矩阵

| 路由路径 | 页面组件 | 主要功能描述 | 关键 API 调用 | 关键 Store | 核心用户交互 |
|----------|----------|-------------|---------------|------------|-------------|
| `/` | WelcomeView | 系统欢迎首页，展示品牌、功能卡片、系统特色，首次访问显示"开始使用"按钮 | 无 | 无 | 点击功能卡片跳转对应页面、点击"开始使用"进入主界面 |
| `/login` | LoginView | 提供用户名/密码登录表单，调用登录 API，成功后存储 Token 并跳转 | POST /api/login | useAuthStore (handleLoginSuccess) | 输入用户名密码、点击登录、查看登录错误提示 |
| `/403` | ForbiddenView | 显示 403 无权限提示，列出可能原因，提供返回首页和联系管理员链接 | 无 | 无 | 点击返回首页、点击联系管理员 |
| `/agreement` | AgreementView | 展示用户协议全文（6 章），需滚动到底部且勾选后方可接受，支持撤回 | 无 | 无 | 阅读协议、滚动到底部、勾选复选框、点击接受/撤回 |
| `/generate` | GenerateView | 无分析数据时的引导页面，提示用户前往分析主界面执行分析 | 无 | useAnalysisStore | 点击"前往分析页面"、点击"返回首页" |
| `/dashboard` | DashboardView | 仪表盘展示统计概览（4 个指标卡片）、快捷操作、近期案件列表 | GET /api/dashboard/stats, GET /api/cases | useCaseStore | 查看统计、点击新建分析、点击查看所有案件、点击案件行进入详情 |
| `/main` | MainView | 核心分析页面，输入案件文本/选择 Demo 案例，调用分析 API 并跳转报告页 | POST /api/analyze, GET /api/cache/stats | useAnalysisStore (currentCaseText, analysisResult, isLoading, cacheHit) | 输入/粘贴文本、选择 Demo 案例、点击"开始分析"、查看缓存分析详情 |
| `/report` | ReportView | 完整分析报告（11 章节），含章节导航/审查清单/维度矩阵/下载 PDF&DOCX | POST /api/reports/generate, GET /api/reports/:id, GET /api/reports/:id/pdf, GET /api/reports/:id/docx, POST /api/reports/:id/review | useAnalysisStore (analysisResult) | 点击章节导航、勾选审查项、标记章节、下载 PDF/DOCX、保存审查 |
| `/cases` | CasesView | 案件列表管理，支持搜索、状态筛选、分页、新建案件、删除案件 | GET /api/cases, POST /api/cases, DELETE /api/cases/:id | useCaseStore (caseList, totalCases, currentPage) | 搜索案件、筛选状态、翻页、新建案件对话框、点击查看详情、删除确认 |
| `/cases/:id` | CaseDetailView | 案件详情展示案件信息和分析结果摘要，支持分析/编辑/删除操作 | GET /api/cases/:id, DELETE /api/cases/:id | useCaseStore (currentCase, removeCase) | 查看案件详情、执行分析、查看分析结果、删除确认弹窗 |
| `/review` | ReviewView | 智能阅卷，上传文档提取文本、实体信息抽取、编辑后发送分析 | POST /api/extract, POST /api/extract_entities, POST /api/analyze | useAnalysisStore (setAnalysisResult) | 拖拽/选择文件上传、查看上传进度、富文本编辑、点击"开始抽取"、编辑实体、点击"开始分析" |
| `/analysis` | AnalysisView | 输入案件文本进行分析，展示分析结果、维度矩阵、规则透明度面板 | POST /api/analyze | useAnalysisStore (currentCaseText, analysisResult, isLoading, error) | 输入案件文本、清空文本、点击"开始分析"、查看分析结果/维度矩阵/规则透明度 |
| `/analysis/:id` | AnalysisView | 同 AnalysisView，带路由参数 | POST /api/analyze | useAnalysisStore | 同上 |
| `/upload` | UploadView | 上传案件文件（doc/pdf/txt），展示解析结果并支持编辑后分析 | POST /api/cases/extract | useAnalysisStore (setAnalysisResult) | 拖拽/点击上传文件、查看解析结果、编辑案件信息、保存并分析 |
| `/similar` | SimilarCasesView | 输入案情描述检索相似历史案例，展示相似度/档级/判决结果 | POST /api/cases/similar | 无 | 输入案情描述、点击"开始检索"、查看相似案例结果卡片 |
| `/knowledge` | KnowledgeView | 知识库浏览，分类树导航+标签筛选，卡片/列表视图，搜索排序分页 | GET /api/knowledge, GET /api/knowledge/tags | useKnowledgeStore (entries, tags, total, loading) | 选择分类、筛选标签、搜索、切换视图、翻页、点击条目进入详情、新建知识 |
| `/knowledge/:id` | KnowledgeDetailView | 知识条目详情，Markdown 渲染正文、标签云、关联条目推荐 | GET /api/knowledge/:id, GET /api/knowledge | useKnowledgeStore (currentEntry, fetchEntry, deleteEntry) | 返回列表、编辑/删除条目、查看关联条目、查看 Markdown 渲染内容 |
| `/knowledge/new` | KnowledgeEditView | 新建知识条目，包含标题/分类/信心评分/标签/Markdown 正文编辑 | POST /api/knowledge | useKnowledgeStore (createEntry) | 填写表单、选择分类、添加标签、Markdown 编辑、保存/取消 |
| `/knowledge/:id/edit` | KnowledgeEditView | 编辑知识条目，同新建页面但预填充已有数据 | PUT /api/knowledge/:id, GET /api/knowledge/:id | useKnowledgeStore (updateEntry, fetchEntry) | 同上（编辑模式） |
| `/knowledge-graph` | KnowledgeGraphView | D3.js 知识图谱可视化，筛选面板（分类/标签/关系/搜索），节点点击详情 | GET /api/knowledge/graph, GET /api/knowledge/tags | 无 | 查看图谱、筛选节点/关系、搜索、点击节点跳转详情、查看图例 |
| `/settings` | SettingsView | 系统管理（法律规则 CRUD / 模型版本 / 系统日志 / 用户管理） | GET/POST/PUT/DELETE /api/rules, GET /api/model-version, GET /api/logs, GET/POST /api/users, POST /api/users/:id/reset-password | 无 | 切换标签页、搜索/筛选规则、编辑/删除规则、查看模型指标环形图、日志搜索筛选、用户管理（增/禁/重置密码） |
| `/experiment` | ExperimentView | 受控实验（A/B组），案例展示+计时器+主观明知认定+置信度评分，B组额外展示 AI 分析报告 | GET /api/experiment/progress, GET /api/experiment/assign-case, POST /api/experiment/submit-judgment | 无 | 查看案例、选择明知定性、拖动置信度滑块、填写判断依据、提交判断、B组查看 AI 报告并记录采纳情况 |
| `/eval` | EvalCenterView | 运行系统评测（消融实验/竞品对标），查看结果表格 | POST /api/eval/run, GET /api/eval/latest | 无 | 点击"运行评测"、查看进度、切换消融/竞品标签、导出 CSV/PDF |
| `/labeling` | LabelingView | 案件标注（使用 Element Plus），表格展示+4 类标签下拉编辑+批量标注 | GET /api/cases, GET /api/cases/:id/labels, POST /api/cases/:id/labels, DELETE /api/cases/:id/labels | 无 | 搜索/筛选案件、编辑 4 类标签、单行保存、批量标注、查看统计条、查看详情抽屉 |

---

## 13. 关键发现与风险点

### 13.1 架构优势
- **清晰的分层结构**：views/components/stores/api/utils 职责分明
- **良好的错误处理**：Axios 响应拦截器统一处理 401/403/404/413/429/5xx
- **代码拆分**：路由级懒加载（所有页面组件均为动态 import）
- **Sentry 集成**：错误追踪+性能监控+会话回放

### 13.2 需关注问题

| 问题 | 严重性 | 说明 |
|------|--------|------|
| `Sentry` 在 router/index.js 中未导入 | 高 | 第 164 行使用 Sentry.addBreadcrumb 但无 import |
| LabelingView 使用 Element Plus | 中 | 仅此页面使用，增加约 117KB 打包体积 |
| KnowledgeEditView chunk 过大 | 中 | 873KB（含 md-editor-v3），建议代码分割 |
| 多处未使用的函数/变量 | 低 | ReportView(7处)、DimensionMatrix(2处) |
| import/order 不规范 | 低 | main.js、EvalCenterView、LabelingView、SimilarCasesView |
| 测试覆盖率不足 | 中 | 仅 1 个测试文件(WelcomeView)，6 个测试用例 |
| 部分页面属性顺序不规范 | 低 | LabelingView 多处 vue/attributes-order 警告 |
| 无 TypeScript | 信息 | 全部使用 JavaScript |
| 无样式预处理器 | 信息 | 纯 CSS + CSS Variables |

---

## 15. 样式方案总结

| 维度 | 结论 |
|------|------|
| 主要样式技术 | **纯 CSS**（CSS Custom Properties） |
| 使用 Sass/SCSS | 否 |
| 使用 Tailwind CSS | 否 |
| 使用 CSS-in-JS | 否 |
| 是否混用 | **否**，全项目统一纯 CSS |
| CSS 变量管理 | `variables.css` → `:root` → 全局可访问 |
| 全局样式 | `global.css`（reset + 工具类） |
| 组件样式 | 全部 `<style scoped>` |
| 响应式方案 | 原生 `@media` 查询 |

---

## 16. 目录结构总结

```
frontend/src/
├── api/              # API 接口层 (4 文件)
│   ├── client.js         # Axios 封装客户端
│   ├── auth.js           # 认证相关 API
│   ├── cases.js          # 案件 CRUD API
│   └── analysis.js       # 分析与知识库 API
├── assets/
│   └── styles/
│       ├── variables.css # CSS 变量
│       └── global.css    # 全局样式
├── components/       # 可复用组件 (7 文件)
│   ├── analysis/         # 分析相关组件 (3)
│   ├── cases/            # 案件组件 (1)
│   ├── common/           # 通用组件 (3)
│   └── KnowledgeGraph.vue # 知识图谱组件
├── data/             # 静态数据 (2 文件)
│   ├── config.js         # 配置常量
│   └── demoCases.js      # Demo 案例数据
├── router/
│   └── index.js          # 路由配置 + 守卫
├── stores/           # Pinia Store (4 文件)
│   ├── index.js          # 导出聚合
│   ├── analysisStore.js  # 分析状态
│   ├── auth.js           # 认证状态
│   ├── case.js           # 案件状态
│   └── knowledgeStore.js # 知识库状态
├── utils/            # 工具函数 (6 文件)
│   ├── agreement.js      # 协议状态管理
│   ├── auth.js           # JWT 处理/Token 刷新
│   ├── errorHandler.js   # 错误分类/日志
│   ├── errorPlugin.js    # Vue 全局错误插件
│   ├── formatters.js     # 日期/文本格式化
│   ├── storage.js        # localStorage 封装
│   └── validators.js     # 表单验证
├── views/            # 页面组件 (22 文件)
│   ├── *.vue             # 21 个页面组件
│   └── research/
│       └── ExperimentView.vue
├── App.vue           # 根组件
└── main.js           # 应用入口
```

---

## 17. 构建产物对比基线

| 项目 | 当前值 |
|------|--------|
| 构建工具 | Vite 5.4.21 |
| 构建耗时 | 1m 19s |
| 产物目录 | `frontend/dist/` |
| 入口 HTML | 0.47 KB |
| 最大 JS 文件 | KnowledgeEditView (873 KB) |
| 第二大 JS 文件 | LabelingView (117 KB) |
| 最大 CSS 文件 | KnowledgeEditView (77.9 KB) |
| 特殊警告 | `@vueuse/core` `__PURE__` 注释位置问题 |
| 构建状态 | ✅ 成功 |

### 11.4 开发服务器验证 (`npm run dev`)

| 指标 | 数值 |
|------|------|
| 启动状态 | ✅ 成功 |
| 监听地址 | http://localhost:3000/ |
| 网络地址 | http://192.168.1.17:3000/ |
| 启动耗时 | 1983ms |
| 热更新 | ✅ 正常工作（文件变更自动 reload） |
| 运行时错误 | 1 个（已修复） |

#### 修复：Sentry 未导入问题
- **问题**：[router/index.js](file:///c:/Users/Lenovo/Desktop/帮信罪辅助裁定软件/frontend/src/router/index.js) 第 164 行使用 `Sentry.addBreadcrumb()` 但未导入 Sentry 模块
- **表现**：页面加载时抛出 `ReferenceError: Sentry is not defined`
- **修复**：添加 `import * as Sentry from '@sentry/vue'`
- **验证**：修复后热更新自动重新加载，运行时错误消除

### 11.5 浏览器验证说明

浏览器验证需要**人工操作**，建议按以下步骤验证：

1. 启动开发服务器：`npm run dev`
2. 在 Chrome/Firefox/Edge 中访问 http://localhost:3000/
3. 逐一路径验证（共 24 个路由），检查：
   - 页面渲染是否正常
   - 控制台无错误输出
   - 基本交互功能可用
4. 重点关注需要后端 API 的页面（登录、分析、案件等），验证前端 UI 在 API 未响应时的错误状态显示

> **注意**：由于前端强依赖后端 API（/api/*），多数页面（如 /main、/cases、/report 等）在不启动后端服务时仅能验证页面框架渲染是否正确，API 调用会返回网络错误，这是预期行为。

---

## 14. 已执行修复

在分析过程中发现并修复了以下问题：

| 问题 | 文件 | 修复 |
|------|------|------|
| `Sentry` 未导入 | `src/router/index.js` | 添加 `import * as Sentry from '@sentry/vue'` |

---

*报告结束。本报告记录了前端系统的完整基线信息，可作为后续重构工作的功能基准和对比依据。*
