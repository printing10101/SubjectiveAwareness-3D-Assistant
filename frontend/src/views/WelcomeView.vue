<script setup>
import { ref, onMounted } from 'vue'

import { useRouter } from 'vue-router'

const router = useRouter()
const isFirstVisit = ref(true)

onMounted(() => {
  // 检查是否为首次访问
  const hasVisited = localStorage.getItem('hasVisitedWelcome')
  if (hasVisited === 'true') {
    // 非首次访问，直接进入主界面
    isFirstVisit.value = false
    router.push('/main')
  }
})

function handleStartUsing() {
  localStorage.setItem('hasVisitedWelcome', 'true')
  router.push('/main')
}

function handleAnalyzeNewCase() {
  localStorage.setItem('hasVisitedWelcome', 'true')
  router.push('/upload')
}

function handleViewHistory() {
  router.push('/cases')
}

function handleViewKnowledge() {
  router.push('/knowledge')
}

function handleSearchSimilarCases() {
  router.push('/similar')
}
</script>

<template>
  <div class="welcome-page">
    <div class="welcome-content">
      <div class="welcome-header">
        <h1 class="welcome-title">
          帮信罪辅助裁定系统
        </h1>
        <p class="welcome-subtitle">
          AI驱动的法律分析工具，专注于帮助信息网络犯罪活动罪的智能辅助裁判
        </p>
      </div>

      <div class="main-actions">
        <button
          class="action-card primary"
          @click="handleAnalyzeNewCase"
        >
          <div class="card-icon">📊</div>
          <h2 class="card-title">分析新案件</h2>
          <p class="card-desc">上传案件材料，获取多维度智能分析</p>
        </button>

        <button
          class="action-card"
          @click="handleViewHistory"
        >
          <div class="card-icon">📋</div>
          <h2 class="card-title">我的历史分析</h2>
          <p class="card-desc">查看过往分析记录与报告</p>
        </button>

        <button
          class="action-card"
          @click="handleViewKnowledge"
        >
          <div class="card-icon">📚</div>
          <h2 class="card-title">帮信罪法律知识</h2>
          <p class="card-desc">学习相关法律法规与司法解释</p>
        </button>

        <button
          class="action-card"
          @click="handleSearchSimilarCases"
        >
          <div class="card-icon">🔍</div>
          <h2 class="card-title">相似案例检索</h2>
          <p class="card-desc">检索相似历史案例，参考裁判结果</p>
        </button>
      </div>

      <div class="welcome-card card">
        <h2 class="section-title">
          系统简介
        </h2>
        <p class="section-desc">
          本系统基于大语言模型（LLM），针对"帮助信息网络犯罪活动罪"中
          <strong>"主观明知"</strong>这一核心要素，提供多维度、可溯源的辅助分析。
        </p>

        <div class="features-grid">
          <div class="feature-item">
            <div class="feature-icon">
              📊
            </div>
            <h3 class="feature-title">
              多维度分析
            </h3>
            <p class="feature-desc">
              从交易异常性、沟通内容、嫌疑人行为三个维度进行全面分析
            </p>
          </div>

          <div class="feature-item">
            <div class="feature-icon">
              🔗
            </div>
            <h3 class="feature-title">
              推理链溯源
            </h3>
            <p class="feature-desc">
              清晰展示"证据 → 规则 → 结论"的完整逻辑链条
            </p>
          </div>

          <div class="feature-item">
            <div class="feature-icon">
              📚
            </div>
            <h3 class="feature-title">
              法条引用
            </h3>
            <p class="feature-desc">
              自动引用相关法律法规，提供法律依据支撑
            </p>
          </div>

          <div class="feature-item">
            <div class="feature-icon">
              📋
            </div>
            <h3 class="feature-title">
              报告生成
            </h3>
            <p class="feature-desc">
              一键生成 Markdown 格式分析报告，支持复制导出
            </p>
          </div>
        </div>

        <div class="welcome-tips">
          <h3 class="tips-title">
            💡 使用提示
          </h3>
          <ul class="tips-list">
            <li>上传案件材料（支持 .doc、.pdf、.txt 格式）</li>
            <li>系统自动进行多维度分析，生成详细报告</li>
            <li>可查看推理依据、相似案例和法律依据</li>
            <li>所有分析结果仅供参考，不构成法律意见</li>
          </ul>
        </div>
      </div>

      <button
        v-if="isFirstVisit"
        class="btn btn-primary btn-lg start-btn"
        @click="handleStartUsing"
      >
        开始使用
      </button>
    </div>
  </div>
</template>

<style scoped>
.welcome-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem 1rem;
}

.welcome-content {
  max-width: 1000px;
  width: 100%;
}

.welcome-header {
  text-align: center;
  margin-bottom: 2.5rem;
  color: white;
}

.welcome-title {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.welcome-subtitle {
  font-size: 1.125rem;
  opacity: 0.9;
  max-width: 600px;
  margin: 0 auto;
}

.main-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2.5rem;
}

.action-card {
  background: white;
  border: none;
  border-radius: var(--border-radius-lg);
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-md);
}

.action-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.action-card.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.action-card.primary .card-title,
.action-card.primary .card-desc {
  color: white;
}

.card-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.5rem;
}

.card-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
}

.welcome-card {
  background: white;
  margin-bottom: 2rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1rem;
}

.section-desc {
  font-size: 1.125rem;
  color: var(--text-secondary);
  margin-bottom: 2rem;
  line-height: 1.8;
}

.features-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

@media (min-width: 640px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.feature-item {
  padding: 1.25rem;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
  transition: transform var(--transition-fast);
}

.feature-item:hover {
  transform: translateY(-2px);
}

.feature-icon {
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.feature-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.feature-desc {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.welcome-tips {
  padding: 1.25rem;
  background: #fef3c7;
  border-radius: var(--border-radius);
  border-left: 4px solid #eab308;
}

.tips-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: #92400e;
}

.tips-list {
  padding-left: 1.25rem;
  color: #78350f;
}

.tips-list li {
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.start-btn {
  display: block;
  width: 100%;
  max-width: 300px;
  margin: 0 auto;
  padding: 1rem 2rem;
  font-size: 1.25rem;
  background: white;
  color: var(--color-primary);
  font-weight: 600;
  border: none;
  border-radius: var(--border-radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-lg);
}

.start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 20px -3px rgba(0, 0, 0, 0.15);
}

@media (max-width: 768px) {
  .welcome-title {
    font-size: 1.75rem;
  }

  .welcome-subtitle {
    font-size: 1rem;
  }

  .section-desc {
    font-size: 1rem;
  }

  .main-actions {
    grid-template-columns: 1fr;
  }
}
</style>
