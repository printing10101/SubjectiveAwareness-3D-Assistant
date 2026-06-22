<script setup>
// 1. 导入语句
import { ref, computed, onMounted, nextTick } from 'vue'

import axios from 'axios'
import { useRouter } from 'vue-router'

import { useAnalysisStore } from '../stores/analysisStore.js'
import StandardPathBadge from '../components/analysis/StandardPathBadge.vue'
import MultiSubjectPanel from '../components/analysis/MultiSubjectPanel.vue'
import EvidenceLayerPanel from '../components/analysis/EvidenceLayerPanel.vue'
import BoundaryAlertBanner from '../components/analysis/BoundaryAlertBanner.vue'

// 导入拆分后的组件
import ReportHeader from '../components/report/ReportHeader.vue'
import ReportChapterNav from '../components/report/ReportChapterNav.vue'
import ReportReviewChecklist from '../components/report/ReportReviewChecklist.vue'
import ReportChapterSection from '../components/report/ReportChapterSection.vue'

// 4. 组合式函数
const router = useRouter()
const store = useAnalysisStore()

// 5. 响应式数据
const activeChapter = ref('ch1')
const isGenerating = ref(false)
const isDownloadingPdf = ref(false)
const isDownloadingDocx = ref(false)
const reportId = ref(null)
const reportContent = ref(null)
const reviewItems = ref({})
const markedSections = ref(new Set())
const hoveredCitation = ref(null)
const citationPosition = ref({ top: 0, left: 0 })
const isAllSelected = ref(false)

// 章节配置
const chapterConfig = [
  { id: 'ch1', title: '基本信息', icon: '📋' },
  { id: 'ch2', title: '事实摘要', icon: '📝' },
  { id: 'ch3', title: '维度分析', icon: '📊' },
  { id: 'ch4', title: '触发规则', icon: '⚠️' },
  { id: 'ch5', title: '事实标签', icon: '🏷️' },
  { id: 'ch6', title: '冲突结果', icon: '⚡' },
  { id: 'ch7', title: '相似案例', icon: '📚' },
  { id: 'ch8', title: '量刑建议', icon: '⚖️' },
  { id: 'ch9', title: '法律依据', icon: '📖' },
  { id: 'ch10', title: '审查结论', icon: '✅' },
  { id: 'ch11', title: '附录说明', icon: '📎' },
]

// 6. 计算属性
const result = computed(() => store.analysisResult)
const hasResult = computed(() => !!result.value)

const chapters = computed(() => {
  if (!reportContent.value) return generateChaptersFromResult()
  return reportContent.value.chapters || {}
})

const currentChapter = computed(() => {
  return chapters.value[activeChapter.value] || {}
})

const progressPercent = computed(() => {
  const total = Object.keys(reviewItems.value).length
  if (total === 0) return 0
  const completed = Object.values(reviewItems.value).filter(v => v).length
  return Math.round((completed / total) * 100)
})

// 7. 方法
function handleGoBack() {
  router.push('/main')
}

function handleChapterClick(chapterId) {
  activeChapter.value = chapterId
  nextTick(() => {
    const element = document.getElementById(`chapter-${chapterId}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
}

// 滚动监听：高亮当前章节
let scrollObserver = null
function setupScrollObserver() {
  const options = {
    root: null,
    rootMargin: '-100px 0px -60% 0px',
    threshold: 0,
  }

  scrollObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const chapterId = entry.target.id.replace('chapter-', '')
        activeChapter.value = chapterId
      }
    })
  }, options)

  chapterConfig.forEach((chapter) => {
    const element = document.getElementById(`chapter-${chapter.id}`)
    if (element) {
      scrollObserver.observe(element)
    }
  })
}

function cleanupScrollObserver() {
  if (scrollObserver) {
    scrollObserver.disconnect()
    scrollObserver = null
  }
}

// 引用段落 hover 处理
function handleCitationMouseEnter(event, citation) {
  hoveredCitation.value = citation
  const rect = event.target.getBoundingClientRect()
  citationPosition.value = {
    top: rect.bottom + window.scrollY + 8,
    left: rect.left + window.scrollX,
  }
}

function handleCitationMouseLeave() {
  hoveredCitation.value = null
}

// 审查清单全选/取消全选
function handleToggleAll() {
  const newValue = !isAllSelected.value
  isAllSelected.value = newValue
  Object.keys(reviewItems.value).forEach((key) => {
    reviewItems.value[key] = newValue
  })
  saveReviewStateToStorage()
}

// 保存审查状态到 localStorage
function saveReviewStateToStorage() {
  try {
    const state = {
      reviewItems: reviewItems.value,
      timestamp: Date.now(),
    }
    localStorage.setItem('reportReviewState', JSON.stringify(state))
  } catch (err) {
    console.error('保存审查状态失败:', err)
  }
}

// 从 localStorage 恢复审查状态
function loadReviewStateFromStorage() {
  try {
    const saved = localStorage.getItem('reportReviewState')
    if (saved) {
      const state = JSON.parse(saved)
      // 检查是否超过7天，超过则清除
      const daysDiff = (Date.now() - state.timestamp) / (1000 * 60 * 60 * 24)
      if (daysDiff > 7) {
        localStorage.removeItem('reportReviewState')
        return false
      }
      if (state.reviewItems) {
        reviewItems.value = state.reviewItems
        updateAllSelectedState()
        return true
      }
    }
  } catch (err) {
    console.error('恢复审查状态失败:', err)
  }
  return false
}

// 更新全选状态
function updateAllSelectedState() {
  const values = Object.values(reviewItems.value)
  isAllSelected.value = values.length > 0 && values.every((v) => v)
}

function handleMarkSection(chapterId) {
  if (markedSections.value.has(chapterId)) {
    markedSections.value.delete(chapterId)
  } else {
    markedSections.value.add(chapterId)
  }
}

function isMarked(chapterId) {
  return markedSections.value.has(chapterId)
}

function generateChaptersFromResult() {
  if (!result.value) return {}

  const r = result.value
  const now = new Date().toISOString()

  return {
    ch1: {
      chapter_id: 'ch1',
      title: '第一章 基本信息',
      sections: [
        {
          heading: '案件信息',
          content: `分析日期: ${now}`,
        },
        {
          heading: '案件编号',
          content: `CASE-${Date.now()}`,
        },
      ],
      citations: [],
    },
    ch2: {
      chapter_id: 'ch2',
      title: '第二章 事实摘要',
      sections: [
        {
          heading: '核心事实',
          content: r.overall_summary || '暂无事实摘要',
        },
      ],
      citations: [],
    },
    ch3: {
      chapter_id: 'ch3',
      title: '第三章 维度分析',
      sections: generateDimensionSections(r),
      citations: [],
    },
    ch4: {
      chapter_id: 'ch4',
      title: '第四章 触发规则',
      sections: generateTriggeredRulesSections(r),
      citations: [],
    },
    ch5: {
      chapter_id: 'ch5',
      title: '第五章 事实标签',
      sections: generateFactTagsSections(r),
      citations: [],
    },
    ch6: {
      chapter_id: 'ch6',
      title: '第六章 冲突结果',
      sections: generateConflictSections(r),
      citations: [],
    },
    ch7: {
      chapter_id: 'ch7',
      title: '第七章 相似案例',
      sections: [],
      citations: [],
    },
    ch8: {
      chapter_id: 'ch8',
      title: '第八章 量刑建议',
      sections: generateSentencingSections(r),
      citations: [],
    },
    ch9: {
      chapter_id: 'ch9',
      title: '第九章 法律依据',
      sections: generateLegalBasisSections(r),
      citations: [],
    },
    ch10: {
      chapter_id: 'ch10',
      title: '第十章 审查结论',
      sections: generateConclusionSections(r),
      citations: [],
    },
  }
}

function generateDimensionSections(r) {
  const sections = []
  if (r.dimensions) {
    for (const [key, dim] of Object.entries(r.dimensions)) {
      sections.push({
        heading: key,
        content: dim.conclusion || '暂无结论',
        score: dim.score,
        reasoning: dim.reasoning,
      })
    }
  }
  return sections
}

function generateTriggeredRulesSections(r) {
  const sections = []
  if (r.reasoning_chains) {
    r.reasoning_chains.forEach((chain, idx) => {
      sections.push({
        heading: `规则 ${idx + 1}`,
        content: chain.rule || '无',
        evidence: chain.evidence,
        conclusion: chain.conclusion,
      })
    })
  }
  return sections
}

function generateFactTagsSections(r) {
  const sections = []
  if (r.dimensions) {
    const tags = Object.keys(r.dimensions)
    sections.push({
      heading: '识别标签',
      tags: tags,
      content: tags.join(', '),
    })
  }
  return sections
}

function generateConflictSections(r) {
  const sections = []
  if (r.conclusion === '边缘情况') {
    sections.push({
      heading: '矛盾点分析',
      content: '本案存在主观明知认定的矛盾点，需要进一步审查证据',
    })
  } else {
    sections.push({
      heading: '一致性分析',
      content: '各维度分析结论一致，无明显矛盾点',
    })
  }
  return sections
}

function generateSentencingSections(r) {
  const sections = []
  if (r.conclusion === '明显明知') {
    sections.push({
      heading: '量刑建议',
      content: '建议判处有期徒刑，具体刑期需结合涉案金额和情节',
      tier_label: 'T3 情节严重',
      sentence_band: '3-7年',
    })
  } else if (r.conclusion === '确实不明知') {
    sections.push({
      heading: '量刑建议',
      content: '建议不起诉或免予刑事处罚',
      tier_label: 'T1 情节较轻',
      sentence_band: '0-1年',
    })
  } else {
    sections.push({
      heading: '量刑建议',
      content: '建议进一步调查后确定量刑',
      tier_label: 'T2 情节一般',
      sentence_band: '1-3年',
    })
  }
  return sections
}

function generateLegalBasisSections(r) {
  return [
    {
      heading: '主要法律依据',
      laws: [
        { law: '刑法', article: '第二百八十七条之二', content: '帮助信息网络犯罪活动罪' },
        { law: '司法解释', article: '法释〔2019〕18号', content: '关于办理非法利用信息网络、帮助信息网络犯罪活动等刑事案件适用法律若干问题的解释' },
      ],
      content: '刑法第二百八十七条之二及相关司法解释',
    },
  ]
}

function generateConclusionSections(r) {
  return [
    {
      heading: '综合结论',
      content: r.overall_summary || '暂无结论',
      conclusion: r.conclusion || '未知',
      confidence: r.confidence,
    },
    {
      heading: '审查建议',
      content: '请结合全案证据，综合判断嫌疑人主观明知状态',
    },
  ]
}

async function handleGenerateReport() {
  if (!result.value) return

  isGenerating.value = true
  try {
    const resp = await axios.post('/api/reports/generate', {
      analysis_id: result.value.id || 1,
    })
    reportId.value = resp.data.report_id

    const reportResp = await axios.get(`/api/reports/${reportId.value}`)
    reportContent.value = reportResp.data.content

    initReviewItems()
  } catch (err) {
    console.error('报告生成失败:', err)
    reportContent.value = { chapters: generateChaptersFromResult() }
    initReviewItems()
  } finally {
    isGenerating.value = false
  }
}

function initReviewItems() {
  const items = {}
  chapterConfig.forEach(ch => {
    items[ch.id] = false
  })
  reviewItems.value = items
}

async function handleDownloadPdf() {
  if (!reportId.value) {
    await handleGenerateReport()
  }

  isDownloadingPdf.value = true
  try {
    const resp = await axios.get(`/api/reports/${reportId.value}/pdf`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([resp.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${reportId.value}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('PDF下载失败:', err)
    alert('PDF下载失败，请稍后重试')
  } finally {
    isDownloadingPdf.value = false
  }
}

async function handleDownloadDocx() {
  if (!reportId.value) {
    await handleGenerateReport()
  }

  isDownloadingDocx.value = true
  try {
    const resp = await axios.get(`/api/reports/${reportId.value}/docx`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([resp.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${reportId.value}.docx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('DOCX下载失败:', err)
    alert('DOCX下载失败，请稍后重试')
  } finally {
    isDownloadingDocx.value = false
  }
}

async function handleSaveReview() {
  if (!reportId.value) return

  try {
    await axios.post(`/api/reports/${reportId.value}/review`, {
      items: reviewItems.value,
      comments: '审查意见',
    })
    alert('审查结果保存成功')
  } catch (err) {
    console.error('审查保存失败:', err)
    alert('审查保存失败，请稍后重试')
  }
}

function handleToggleReview(chapterId) {
  reviewItems.value[chapterId] = !reviewItems.value[chapterId]
}

// 8. 生命周期
onMounted(() => {
  if (!hasResult.value) {
    router.push('/main')
    return
  }
  initReviewItems()
  reportContent.value = { chapters: generateChaptersFromResult() }
})
</script>

<template>
  <div class="report-page">
    <div
      v-if="!hasResult"
      class="report-empty"
    >
      <div class="loading-spinner"></div>
      <p>正在加载分析报告...</p>
    </div>

    <div
      v-else
      class="report-layout"
    >
      <!-- 顶部操作栏 -->
      <ReportHeader
        :is-downloading-pdf="isDownloadingPdf"
        :is-downloading-docx="isDownloadingDocx"
        @download-pdf="handleDownloadPdf"
        @download-docx="handleDownloadDocx"
        @go-back="handleGoBack"
      />

      <!-- 主内容区 -->
      <div class="report-main">
        <!-- 左侧导航 -->
        <aside class="report-sidebar">
          <ReportChapterNav
            :chapters="chapterConfig"
            :active-chapter="activeChapter"
            :marked-sections="markedSections"
            @chapter-click="handleChapterClick"
          />

          <!-- 审查清单 -->
          <ReportReviewChecklist
            :chapters="chapterConfig"
            :review-items="reviewItems"
            :is-all-selected="isAllSelected"
            :progress-percent="progressPercent"
            @toggle-all="handleToggleAll"
            @toggle-review="handleToggleReview"
            @save-review="handleSaveReview"
          />
        </aside>

        <!-- 右侧内容区 -->
        <main class="report-content">
          <!-- 规范路径标签展示区 -->
          <div v-if="result?.standardPaths?.length" class="standard-paths-section">
            <h3 class="section-title">规范路径标签</h3>
            <div class="paths-container">
              <StandardPathBadge
                v-for="(path, index) in result.standardPaths"
                :key="index"
                :path-type="path.pathType"
                :label="path.label"
                :description="path.description"
              />
            </div>
          </div>

          <!-- 多主体列表展示区 -->
          <div v-if="result?.subjects?.length" class="subjects-section">
            <h3 class="section-title">涉案主体</h3>
            <MultiSubjectPanel :subjects="result.subjects" />
          </div>

          <!-- 证据四层折叠展示区 -->
          <div v-if="result?.evidenceLayers" class="evidence-section">
            <h3 class="section-title">证据分层</h3>
            <EvidenceLayerPanel :evidence-layers="result.evidenceLayers" />
          </div>

          <!-- 边界警告徽章展示区 -->
          <div v-if="result?.boundaryAlerts?.length" class="boundary-alerts-section">
            <BoundaryAlertBanner :alerts="result.boundaryAlerts" />
          </div>

          <!-- 数据可视化矩阵 -->
          <div class="visualization-card">
            <h3 class="card-title">分析维度矩阵</h3>
            <div class="matrix-grid">
              <div
                v-for="chapter in chapterConfig.slice(0, 12)"
                :key="chapter.id"
                class="matrix-cell"
                :class="{ completed: reviewItems[chapter.id] }"
              >
                <span class="cell-icon">{{ chapter.icon }}</span>
                <span class="cell-label">{{ chapter.title }}</span>
              </div>
            </div>
          </div>

          <!-- 章节内容 -->
          <ReportChapterSection
            v-for="chapter in chapterConfig"
            :key="chapter.id"
            :chapter="chapter"
            :chapter-data="chapters[chapter.id]"
            :is-marked="isMarked(chapter.id)"
            @mark-section="handleMarkSection"
          />
        </main>
      </div>

      <!-- 引用段落提示框 -->
      <div
        v-if="hoveredCitation"
        class="citation-tooltip"
        :style="{
          top: `${citationPosition.top}px`,
          left: `${citationPosition.left}px`,
        }"
      >
        <div class="citation-content">
          <strong>引用原文：</strong>
          <p>{{ hoveredCitation }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.report-page {
  min-height: 100vh;
  background: var(--bg-secondary);
}

.report-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 1rem;
  color: var(--text-secondary);
}

.report-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.report-main {
  display: flex;
  flex: 1;
}

.report-sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid var(--border-color);
  padding: 1.5rem;
  position: sticky;
  top: 64px;
  height: calc(100vh - 64px);
  overflow-y: auto;
}

.report-content {
  flex: 1;
  padding: 2rem;
  max-width: calc(100% - 280px);
}

.visualization-card {
  background: white;
  border-radius: var(--border-radius-lg);
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-sm);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 1rem;
}

.matrix-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
}

.matrix-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
  padding: 1rem 0.5rem;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
  border: 2px solid transparent;
  transition: all var(--transition-fast);
}

.matrix-cell.completed {
  background: #dcfce7;
  border-color: #22c55e;
}

.cell-icon {
  font-size: 1.5rem;
}

.cell-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-align: center;
}

.citation-tooltip {
  position: absolute;
  z-index: 1000;
  background: white;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 1rem;
  box-shadow: var(--shadow-lg);
  max-width: 400px;
}

.citation-content strong {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.citation-content p {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--text-secondary);
}

@media (max-width: 1024px) {
  .report-sidebar {
    width: 240px;
  }

  .report-content {
    max-width: calc(100% - 240px);
  }

  .matrix-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .report-main {
    flex-direction: column;
  }

  .report-sidebar {
    width: 100%;
    position: static;
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--border-color);
  }

  .report-content {
    max-width: 100%;
    padding: 1rem;
  }

  .matrix-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
