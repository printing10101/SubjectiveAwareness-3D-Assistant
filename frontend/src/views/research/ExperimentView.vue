<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()

const isAuthenticated = ref(false)
const userInfo = ref(null)
const authLoading = ref(true)

const currentGroup = ref(null)
const currentCase = ref(null)
const currentAssignment = ref(null)
const aiReport = ref(null)
const caseLoading = ref(false)
const caseError = ref(null)

const timerStart = ref(null)
const timerDisplay = ref('00:00.000')
const timerInterval = ref(null)
const reactionTimeMs = ref(0)
const isTimerRunning = ref(false)

const subjectiveKnowledge = ref(null)
const confidenceScore = ref(50)
const reasoningText = ref('')

const aiAdoptionStatus = ref(null)
const aiAdoptionReason = ref('')

const submitting = ref(false)
const submitError = ref(null)
const submitSuccess = ref(false)
const currentSubmission = ref(null)

const progress = ref(null)
const progressLoading = ref(false)

const activeSection = ref('judgment')

onMounted(async () => {
  await checkAuth()
})

onUnmounted(() => {
  stopTimer()
})

async function checkAuth() {
  authLoading.value = true
  const token = localStorage.getItem('access_token')
  if (!token) {
    isAuthenticated.value = false
    authLoading.value = false
    return
  }
  try {
    const resp = await axios.get('/api/me')
    userInfo.value = resp.data
    isAuthenticated.value = true
    await loadProgress()
    await assignNewCase()
  } catch {
    isAuthenticated.value = false
  } finally {
    authLoading.value = false
  }
}

async function loadProgress() {
  try {
    progressLoading.value = true
    const resp = await axios.get('/api/experiment/progress')
    progress.value = resp.data
    if (resp.data.group) {
      currentGroup.value = resp.data.group
    }
  } catch {
    progress.value = null
  } finally {
    progressLoading.value = false
  }
}

async function assignNewCase() {
  caseLoading.value = true
  caseError.value = null
  submitSuccess.value = false
  currentSubmission.value = null
  resetForm()
  try {
    const resp = await axios.get('/api/experiment/assign-case')
    currentAssignment.value = resp.data.assignment
    currentCase.value = resp.data.case
    aiReport.value = resp.data.ai_report || null
    currentGroup.value = resp.data.assignment.group
    await loadProgress()
    startTimer()
  } catch (err) {
    if (err.status === 400) {
      caseError.value = err.message || '所有案例已完成处理'
    } else {
      caseError.value = '获取案例失败，请稍后重试'
    }
  } finally {
    caseLoading.value = false
  }
}

function startTimer() {
  timerStart.value = Date.now()
  isTimerRunning.value = true
  timerInterval.value = setInterval(() => {
    const elapsed = Date.now() - timerStart.value
    reactionTimeMs.value = elapsed
    timerDisplay.value = formatTime(elapsed)
  }, 10)
}

function stopTimer() {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
  }
  isTimerRunning.value = false
}

function formatTime(ms) {
  const totalMs = Math.floor(ms)
  const minutes = Math.floor(totalMs / 60000)
  const seconds = Math.floor((totalMs % 60000) / 1000)
  const millis = totalMs % 1000
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(millis).padStart(3, '0')}`
}

function resetForm() {
  subjectiveKnowledge.value = null
  confidenceScore.value = 50
  reasoningText.value = ''
  aiAdoptionStatus.value = null
  aiAdoptionReason.value = ''
  activeSection.value = 'judgment'
  submitError.value = null
}

async function submitJudgment() {
  if (subjectiveKnowledge.value === null) {
    submitError.value = '请选择主观明知的认定结果'
    return
  }
  if (!reasoningText.value || reasoningText.value.trim().length < 10) {
    submitError.value = '请填写判断依据（不少于10个字符）'
    return
  }

  stopTimer()
  submitting.value = true
  submitError.value = null

  const payload = {
    case_id: currentCase.value.id,
    subjective_knowledge: subjectiveKnowledge.value,
    confidence_score: confidenceScore.value,
    reasoning_text: reasoningText.value.trim(),
    reaction_time_ms: reactionTimeMs.value,
  }

  if (currentGroup.value === 'B' && aiAdoptionStatus.value) {
    payload.ai_adoption = {
      status: aiAdoptionStatus.value,
      reason: aiAdoptionReason.value.trim(),
    }
  }

  try {
    const resp = await axios.post('/api/experiment/submit-judgment', payload)
    currentSubmission.value = resp.data.record
    submitSuccess.value = true
    await loadProgress()
  } catch (err) {
    submitError.value = err.message || '提交失败，请稍后重试'
    startTimer()
  } finally {
    submitting.value = false
  }
}

const isGroupB = computed(() => currentGroup.value === 'B')

const canSubmit = computed(() => (
    subjectiveKnowledge.value !== null &&
    reasoningText.value.trim().length >= 10
  ))

const _statusLabel = computed(() => {
  if (submitSuccess.value) return '已完成'
  if (submitting.value) return '提交中'
  return '待提交'
})

const confidenceLabel = computed(() => {
  const score = confidenceScore.value
  if (score >= 80) return '非常确信'
  if (score >= 60) return '比较确信'
  if (score >= 40) return '一般确信'
  if (score >= 20) return '不太确信'
  return '非常不确定'
})

function formatMs(ms) {
  return formatTime(ms)
}
</script>

<template>
  <div class="experiment-page">
    <div v-if="authLoading" class="loading-container">
      <div class="loading-spinner"></div>
      <p class="loading-text">验证身份中...</p>
    </div>

    <div v-else-if="!isAuthenticated" class="auth-required">
      <div class="auth-card card">
        <div class="auth-icon">🔬</div>
        <h2>实验数据采集系统</h2>
        <p class="auth-desc">
          本系统仅限实验人员使用，请先登录系统。
        </p>
        <button class="btn btn-primary btn-lg" @click="router.push('/')">
          返回登录
        </button>
      </div>
    </div>

    <div v-else class="experiment-container">
      <div class="experiment-header">
        <h1>实验数据采集</h1>
        <div class="header-info">
          <span class="badge" :class="currentGroup === 'A' ? 'badge-a' : 'badge-b'">
            {{ currentGroup ? `实验${currentGroup}组` : '未分组' }}
          </span>
          <span class="experimenter-name">
            {{ userInfo?.username }}
          </span>
        </div>
      </div>

      <div v-if="progress" class="progress-bar-container card">
        <div class="progress-header">
          <span>实验进度</span>
          <span>{{ progress.completed }} / {{ progress.total }} 已完成</span>
        </div>
        <div class="progress-track">
          <div
            class="progress-fill"
            :style="{ width: progress.total > 0 ? (progress.completed / progress.total * 100) + '%' : '0%' }"
          ></div>
        </div>
      </div>

      <div v-if="caseLoading" class="loading-container">
        <div class="loading-spinner"></div>
        <p class="loading-text">正在分配案例...</p>
      </div>

      <div v-else-if="caseError && !currentCase" class="error-state card">
        <div class="error-icon">✅</div>
        <h3>实验已完成</h3>
        <p>{{ caseError }}</p>
        <p class="error-detail">您已完成所有案例的判断，感谢您的参与！</p>
      </div>

      <div v-else-if="currentCase && !submitSuccess" class="experiment-content">
        <div class="case-section card">
          <div class="case-header">
            <h2>{{ currentCase.title }}</h2>
            <div class="timer-display">
              <span class="timer-icon">⏱️</span>
              <span class="timer-value">{{ timerDisplay }}</span>
            </div>
          </div>
          <div class="case-text">
            <p>{{ currentCase.text }}</p>
          </div>
        </div>

        <div class="section-tabs">
          <button
            class="tab-btn"
            :class="{ active: activeSection === 'judgment' }"
            @click="activeSection = 'judgment'"
          >
            判断记录
          </button>
          <button
            v-if="isGroupB && aiReport"
            class="tab-btn"
            :class="{ active: activeSection === 'ai-report' }"
            @click="activeSection = 'ai-report'"
          >
            AI分析报告
          </button>
        </div>

        <div v-if="activeSection === 'judgment'" class="judgment-section card">
          <h3 class="section-title">检察官判断</h3>

          <div class="form-group">
            <label class="form-label">主观明知认定</label>
            <div class="binary-choice">
              <button
                class="choice-btn"
                :class="{ selected: subjectiveKnowledge === true }"
                @click="subjectiveKnowledge = true"
              >
                <span class="choice-icon">✅</span>
                <span class="choice-text">是（具有主观明知）</span>
              </button>
              <button
                class="choice-btn"
                :class="{ selected: subjectiveKnowledge === false }"
                @click="subjectiveKnowledge = false"
              >
                <span class="choice-icon">❌</span>
                <span class="choice-text">否（不具有主观明知）</span>
              </button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">
              置信度评分
              <span class="confidence-label">{{ confidenceLabel }}</span>
            </label>
            <div class="score-slider-container">
              <input
                v-model.number="confidenceScore"
                type="range"
                min="1"
                max="100"
                class="score-slider"
              />
              <div class="score-labels">
                <span>1（非常不确定）</span>
                <span class="score-value">{{ confidenceScore }}</span>
                <span>100（非常确信）</span>
              </div>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">判断依据</label>
            <textarea
              v-model="reasoningText"
              class="form-textarea"
              rows="6"
              placeholder="请详细说明作出上述判断的主要依据，包括对案件事实、证据材料的分析和法律适用的考量..."
            ></textarea>
            <div class="char-count">
              {{ reasoningText.length }} 字符（至少10个字符）
            </div>
          </div>

          <div v-if="submitError" class="submit-error">
            {{ submitError }}
          </div>

          <button
            class="btn btn-primary btn-lg submit-btn"
            :disabled="!canSubmit || submitting"
            @click="submitJudgment"
          >
            {{ submitting ? '提交中...' : '提交判断' }}
          </button>
        </div>

        <div v-if="activeSection === 'ai-report' && aiReport" class="ai-report-section card">
          <h3 class="section-title">AI分析报告</h3>

          <div class="report-score">
            <div class="score-item">
              <span class="score-label">知识图谱得分</span>
              <span class="score-value-big" :class="aiReport.knowledge_score >= 70 ? 'score-high' : aiReport.knowledge_score >= 40 ? 'score-mid' : 'score-low'">
                {{ aiReport.knowledge_score }}
              </span>
            </div>
          </div>

          <div class="report-dimension">
            <h4>行为异常评估</h4>
            <div class="dimension-header">
              <span class="dimension-score" :class="aiReport.behavior_assessment.score >= 70 ? 'score-high' : aiReport.behavior_assessment.score >= 40 ? 'score-mid' : 'score-low'">
                {{ aiReport.behavior_assessment.score }}分 - {{ aiReport.behavior_assessment.level }}
              </span>
            </div>
            <p class="dimension-text">{{ aiReport.behavior_assessment.analysis }}</p>
            <ul v-if="aiReport.behavior_assessment.key_factors" class="factor-list">
              <li v-for="(factor, idx) in aiReport.behavior_assessment.key_factors" :key="idx">
                {{ factor }}
              </li>
            </ul>
          </div>

          <div class="report-dimension">
            <h4>认知能力匹配</h4>
            <div class="dimension-header">
              <span class="dimension-score" :class="aiReport.cognitive_assessment.score >= 70 ? 'score-high' : aiReport.cognitive_assessment.score >= 40 ? 'score-mid' : 'score-low'">
                {{ aiReport.cognitive_assessment.score }}分 - {{ aiReport.cognitive_assessment.level }}
              </span>
            </div>
            <p class="dimension-text">{{ aiReport.cognitive_assessment.analysis }}</p>
          </div>

          <div class="report-dimension">
            <h4>辩护合理性评估</h4>
            <div class="dimension-header">
              <span class="dimension-score" :class="aiReport.defense_assessment.score >= 70 ? 'score-high' : aiReport.defense_assessment.score >= 40 ? 'score-mid' : 'score-low'">
                {{ aiReport.defense_assessment.score }}分 - {{ aiReport.defense_assessment.level }}
              </span>
            </div>
            <p class="dimension-text">{{ aiReport.defense_assessment.analysis }}</p>
          </div>

          <div class="report-summary">
            <h4>综合结论</h4>
            <p>{{ aiReport.overall_summary }}</p>
          </div>

          <div class="report-evidence">
            <h4>证据参考</h4>
            <ul>
              <li v-for="(evRef, idx) in aiReport.evidence_refs" :key="idx">{{ evRef }}</li>
            </ul>
          </div>

          <div class="adoption-section">
            <h4>AI建议采纳记录</h4>
            <div class="form-group">
              <label class="form-label">采纳状态</label>
              <div class="adoption-choices">
                <button
                  class="choice-btn adoption-btn"
                  :class="{ selected: aiAdoptionStatus === 'fully_adopted' }"
                  @click="aiAdoptionStatus = 'fully_adopted'"
                >
                  完全采纳
                </button>
                <button
                  class="choice-btn adoption-btn"
                  :class="{ selected: aiAdoptionStatus === 'partially_adopted' }"
                  @click="aiAdoptionStatus = 'partially_adopted'"
                >
                  部分采纳
                </button>
                <button
                  class="choice-btn adoption-btn"
                  :class="{ selected: aiAdoptionStatus === 'not_adopted' }"
                  @click="aiAdoptionStatus = 'not_adopted'"
                >
                  不采纳
                </button>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">采纳/不采纳理由</label>
              <textarea
                v-model="aiAdoptionReason"
                class="form-textarea"
                rows="3"
                placeholder="请说明采纳或不采纳AI建议的理由..."
              ></textarea>
            </div>
          </div>
        </div>
      </div>

      <div v-if="submitSuccess" class="success-state card">
        <div class="success-icon">✅</div>
        <h3>提交成功</h3>
        <div class="submission-summary">
          <div class="summary-row">
            <span class="summary-label">案例</span>
            <span class="summary-value">{{ currentCase?.title }}</span>
          </div>
          <div class="summary-row">
            <span class="summary-label">主观明知认定</span>
            <span class="summary-value" :class="currentSubmission?.subjective_knowledge ? 'text-danger' : 'text-success'">
              {{ currentSubmission?.subjective_knowledge ? '是' : '否' }}
            </span>
          </div>
          <div class="summary-row">
            <span class="summary-label">置信度</span>
            <span class="summary-value">{{ currentSubmission?.confidence_score }}/100</span>
          </div>
          <div class="summary-row">
            <span class="summary-label">反应时长</span>
            <span class="summary-value">{{ formatMs(currentSubmission?.reaction_time_ms) }}</span>
          </div>
        </div>
        <div class="success-actions">
          <button class="btn btn-primary btn-lg" @click="assignNewCase">
            {{ progress && progress.pending > 0 ? '下一个案例' : '查看结果' }}
          </button>
          <button class="btn btn-secondary" @click="router.push('/main')">
            返回主页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.experiment-page {
  min-height: calc(100vh - 56px);
  background: var(--bg-secondary);
  padding: 1.5rem;
}

.experiment-container {
  max-width: 960px;
  margin: 0 auto;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  gap: 1rem;
}

.loading-text {
  color: var(--text-secondary);
  font-size: 1rem;
}

.auth-required {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 56px);
  padding: 2rem;
}

.auth-card {
  text-align: center;
  max-width: 480px;
  padding: 3rem 2rem;
}

.auth-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.auth-card h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: var(--text-primary);
}

.auth-desc {
  color: var(--text-secondary);
  margin-bottom: 2rem;
  line-height: 1.6;
}

.experiment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.experiment-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 600;
}

.badge-a {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge-b {
  background: #fce7f3;
  color: #db2777;
}

.experimenter-name {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.progress-bar-container {
  margin-bottom: 1.5rem;
  padding: 1rem 1.5rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.progress-track {
  width: 100%;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), #818cf8);
  border-radius: 9999px;
  transition: width 0.5s ease;
}

.error-state {
  text-align: center;
  padding: 3rem 2rem;
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.error-state h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.error-detail {
  color: var(--text-secondary);
  margin-top: 0.5rem;
}

.experiment-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.case-section {
  padding: 1.5rem;
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.case-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}

.timer-display {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  background: #fef3c7;
  padding: 0.5rem 1rem;
  border-radius: var(--border-radius);
  white-space: nowrap;
}

.timer-icon {
  font-size: 1rem;
}

.timer-value {
  font-family: 'Courier New', Courier, monospace;
  font-size: 1.125rem;
  font-weight: 700;
  color: #92400e;
}

.case-text {
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 1.25rem;
  line-height: 1.8;
  font-size: 0.95rem;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.case-text p {
  margin: 0;
}

.section-tabs {
  display: flex;
  gap: 0.5rem;
}

.tab-btn {
  padding: 0.625rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 500;
  font-family: inherit;
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  background: var(--bg-primary);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.tab-btn:hover {
  color: var(--text-primary);
  background: #f1f5f9;
}

.tab-btn.active {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  font-weight: 600;
}

.judgment-section {
  padding: 1.5rem;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}

.confidence-label {
  font-weight: 400;
  font-size: 0.85rem;
  color: var(--color-primary);
  margin-left: 0.5rem;
}

.binary-choice {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.choice-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: inherit;
  font-size: 0.9rem;
  color: var(--text-primary);
  text-align: left;
}

.choice-btn:hover {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.04);
}

.choice-btn.selected {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
  font-weight: 600;
}

.choice-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.choice-text {
  line-height: 1.3;
}

.score-slider-container {
  padding: 0.5rem 0;
}

.score-slider {
  width: 100%;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: linear-gradient(90deg, #ef4444, #eab308, #22c55e);
  border-radius: 4px;
  outline: none;
  cursor: pointer;
}

.score-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bg-primary);
  border: 3px solid var(--color-primary);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}

.score-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-tertiary);
}

.score-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-primary);
}

.form-textarea {
  width: 100%;
  padding: 0.875rem;
  font-size: 0.9rem;
  font-family: inherit;
  line-height: 1.6;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-primary);
  resize: vertical;
  transition: border-color var(--transition-fast);
}

.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.char-count {
  font-size: 0.8rem;
  color: var(--text-tertiary);
  margin-top: 0.375rem;
  text-align: right;
}

.submit-error {
  padding: 0.75rem 1rem;
  background: #fef2f2;
  color: var(--color-danger);
  border-radius: var(--border-radius);
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.submit-btn {
  width: 100%;
  padding: 1rem;
  font-size: 1.0625rem;
}

.ai-report-section {
  padding: 1.5rem;
}

.report-score {
  margin-bottom: 1.5rem;
}

.score-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.score-label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.score-value-big {
  font-size: 1.5rem;
  font-weight: 700;
}

.score-high {
  color: var(--color-danger);
}

.score-mid {
  color: var(--color-warning);
}

.score-low {
  color: var(--color-success);
}

.report-dimension {
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border-color);
}

.report-dimension h4 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.dimension-header {
  margin-bottom: 0.75rem;
}

.dimension-score {
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  background: var(--bg-secondary);
}

.dimension-text {
  font-size: 0.9rem;
  line-height: 1.7;
  color: var(--text-secondary);
}

.factor-list {
  margin-top: 0.75rem;
  padding-left: 1.25rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.8;
}

.report-summary,
.report-evidence {
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border-color);
}

.report-summary h4,
.report-evidence h4 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.report-summary p,
.report-evidence p {
  font-size: 0.9rem;
  line-height: 1.7;
  color: var(--text-secondary);
}

.report-evidence ul {
  padding-left: 1.25rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.8;
}

.adoption-section {
  padding-top: 0.5rem;
}

.adoption-section h4 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1rem;
}

.adoption-choices {
  display: flex;
  gap: 0.5rem;
}

.adoption-btn {
  flex: 1;
  justify-content: center;
  padding: 0.75rem;
  font-size: 0.85rem;
}

.success-state {
  text-align: center;
  padding: 2.5rem 2rem;
}

.success-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.success-state h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: var(--color-success);
}

.submission-summary {
  max-width: 400px;
  margin: 0 auto 1.5rem;
  text-align: left;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 0.9rem;
}

.summary-row:last-child {
  border-bottom: none;
}

.summary-label {
  color: var(--text-secondary);
}

.summary-value {
  font-weight: 600;
  color: var(--text-primary);
}

.text-success {
  color: var(--color-success);
}

.text-danger {
  color: var(--color-danger);
}

.success-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: center;
}

.success-actions .btn {
  width: 100%;
  max-width: 300px;
}

@media (max-width: 768px) {
  .experiment-page {
    padding: 1rem;
  }

  .experiment-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .binary-choice {
    grid-template-columns: 1fr;
  }

  .adoption-choices {
    flex-direction: column;
  }

  .case-header {
    flex-direction: column;
  }

  .section-tabs {
    overflow-x: auto;
  }
}
</style>
