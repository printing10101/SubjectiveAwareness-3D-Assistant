import { createRouter, createWebHistory } from 'vue-router'

import { useAnalysisStore } from '../stores/analysisStore.js'
import { isAgreementAccepted } from '../utils/agreement.js'
import { isAuthenticated, isAdmin } from '../utils/auth.js'

const routes = [
  {
    path: '/',
    name: 'welcome',
    component: () => import('../views/WelcomeView.vue'),
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('../views/ForbiddenView.vue'),
  },
  {
    // 用户协议与隐私政策页面：始终允许访问，便于用户阅读或重新接受
    path: '/agreement',
    name: 'agreement',
    component: () => import('../views/AgreementView.vue'),
    meta: { requiresAgreement: false, isAgreementPage: true },
  },
  {
    path: '/generate',
    name: 'generate',
    component: () => import('../views/GenerateView.vue'),
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/main',
    name: 'main',
    component: () => import('../views/MainView.vue'),
  },
  {
    path: '/report',
    name: 'report',
    component: () => import('../views/ReportView.vue'),
    meta: { requiresAuth: true, requiresAnalysis: true },
  },
  {
    path: '/cases',
    name: 'cases',
    component: () => import('../views/CasesView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/cases/:id',
    name: 'caseDetail',
    component: () => import('../views/CaseDetailView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/review',
    name: 'review',
    component: () => import('../views/ReviewView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/experiment',
    name: 'experiment',
    component: () => import('../views/research/ExperimentView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import('../views/KnowledgeView.vue'),
    meta: { title: '知识库', requiresKnowledgeAccess: true },
  },
  {
    path: '/knowledge/new',
    name: 'knowledgeNew',
    component: () => import('../views/KnowledgeEditView.vue'),
    meta: { title: '新建知识', requiresAuth: true },
  },
  {
    path: '/knowledge/:id',
    name: 'knowledgeDetail',
    component: () => import('../views/KnowledgeDetailView.vue'),
    meta: { title: '知识详情', requiresKnowledgeAccess: true },
  },
  {
    path: '/knowledge/:id/edit',
    name: 'knowledgeEdit',
    component: () => import('../views/KnowledgeEditView.vue'),
    meta: { title: '编辑知识', requiresAuth: true },
  },
  {
    path: '/knowledge-graph',
    name: 'knowledgeGraph',
    component: () => import('../views/KnowledgeGraphView.vue'),
    meta: { title: '知识图谱', requiresKnowledgeAccess: true },
  },
  {
    path: '/analysis',
    name: 'analysis',
    component: () => import('../views/AnalysisView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/analysis/:id',
    name: 'analysisResult',
    component: () => import('../views/AnalysisView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/upload',
    name: 'upload',
    component: () => import('../views/UploadView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/similar',
    name: 'similar',
    component: () => import('../views/SimilarCasesView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/eval',
    name: 'eval',
    component: () => import('../views/EvalCenterView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    // 案件标注界面：仅 admin / analyst 角色可访问
    path: '/labeling',
    name: 'labeling',
    component: () => import('../views/LabelingView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: '案件标注' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：处理登录验证、权限验证、知识库访问权限、分析结果验证、协议接受验证
router.beforeEach((to, from, next) => {
  // 路由导航面包屑：记录用户访问轨迹，便于 Sentry 复现错误
  Sentry.addBreadcrumb({
    category: 'navigation',
    type: 'navigation',
    level: 'info',
    data: {
      from: from.fullPath,
      to: to.fullPath,
      from_name: from.name || null,
      to_name: to.name || null,
    },
  })

  const authenticated = isAuthenticated()
  const agreementAccepted = isAgreementAccepted()

  // 0. 协议访问控制：未接受协议的用户仅允许访问协议页面与公开页面
  if (!agreementAccepted && to.meta.isAgreementPage !== true) {
    // 允许访问登录页和首页（登录页用于完成登录）
    const isPublicRoute =
      to.name === 'login' || to.name === 'welcome' || to.name === 'forbidden'
    if (!isPublicRoute) {
      next({ name: 'agreement', query: { redirect: to.fullPath } })
      return
    }
  }

  // 1. 需要登录验证
  if (to.meta.requiresAuth) {
    if (!authenticated) {
      next({
        name: 'login',
        query: { redirect: to.fullPath },
      })
      return
    }

    // 如果需要管理员权限
    if (to.meta.requiresAdmin && !isAdmin()) {
      next({ name: 'forbidden' })
      return
    }
  }

  // 2. 知识库访问权限验证
  if (to.meta.requiresKnowledgeAccess) {
    if (!authenticated) {
      next({
        name: 'login',
        query: { redirect: to.fullPath },
      })
      return
    }

    // 区分管理员与普通用户的知识库操作权限
    if (to.meta.requiresAdmin && !isAdmin()) {
      next({ name: 'forbidden' })
      return
    }
  }

  // 3. 如果路由需要分析结果
  if (to.meta.requiresAnalysis) {
    const analysisStore = useAnalysisStore()
    if (!analysisStore.analysisResult) {
      next({ name: 'generate' })
      return
    }
  }

  // 4. 如果用户已登录但尝试访问仅限访客的页面（如登录页）
  if (to.meta.guestOnly && authenticated) {
    next({ name: 'main' })
    return
  }

  // 所有验证通过，允许导航
  next()
})

export default router
