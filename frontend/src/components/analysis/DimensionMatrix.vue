<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  analysisResult: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['dimension-click'])

// 响应式数据
const selectedDimension = ref(null)

// 三维度配置：3行×4列矩阵
const dimensionConfig = [
  // 第一行：交易异常性维度
  { id: 'd1_1', row: 1, col: 1, title: '交易金额', dimension: 'transaction', icon: '💰', description: '分析交易金额是否异常' },
  { id: 'd1_2', row: 1, col: 2, title: '交易频率', dimension: 'transaction', icon: '📊', description: '分析交易频率是否异常' },
  { id: 'd1_3', row: 1, col: 3, title: '交易对象', dimension: 'transaction', icon: '👥', description: '分析交易对象是否可疑' },
  { id: 'd1_4', row: 1, col: 4, title: '交易时间', dimension: 'transaction', icon: '⏰', description: '分析交易时间是否异常' },

  // 第二行：沟通内容维度
  { id: 'd2_1', row: 2, col: 1, title: '聊天记录', dimension: 'communication', icon: '💬', description: '分析聊天内容是否涉及犯罪' },
  { id: 'd2_2', row: 2, col: 2, title: '暗语识别', dimension: 'communication', icon: '🔐', description: '识别是否使用暗语交流' },
  { id: 'd2_3', row: 2, col: 3, title: '指令内容', dimension: 'communication', icon: '📝', description: '分析指令是否可疑' },
  { id: 'd2_4', row: 2, col: 4, title: '沟通方式', dimension: 'communication', icon: '📱', description: '分析沟通方式是否异常' },

  // 第三行：嫌疑人行为维度
  { id: 'd3_1', row: 3, col: 1, title: '行为模式', dimension: 'behavior', icon: '🎭', description: '分析行为模式是否可疑' },
  { id: 'd3_2', row: 3, col: 2, title: '规避手段', dimension: 'behavior', icon: '🛡️', description: '识别是否采取规避手段' },
  { id: 'd3_3', row: 3, col: 3, title: '获利情况', dimension: 'behavior', icon: '💵', description: '分析获利是否异常' },
  { id: 'd3_4', row: 3, col: 4, title: '前科记录', dimension: 'behavior', icon: '📋', description: '查询是否有前科' },
]

// 决策路径树状数据
const decisionTree = ref([
  {
    id: 'root',
    label: '案件分析起点',
    children: [
      {
        id: 'd1',
        label: '维度1: 交易异常性',
        score: 85,
        children: [
          { id: 'd1_1', label: '交易金额异常', score: 90 },
          { id: 'd1_2', label: '交易频率异常', score: 80 },
        ],
      },
      {
        id: 'd2',
        label: '维度2: 沟通内容',
        score: 75,
        children: [
          { id: 'd2_1', label: '发现可疑聊天', score: 85 },
          { id: 'd2_2', label: '识别暗语', score: 65 },
        ],
      },
      {
        id: 'd3',
        label: '维度3: 嫌疑人行为',
        score: 70,
        children: [
          { id: 'd3_1', label: '行为模式可疑', score: 75 },
          { id: 'd3_2', label: '采取规避手段', score: 65 },
        ],
      },
    ],
  },
])

// 计算属性
const hasAnalysisResult = computed(() => !!props.analysisResult)

const dimensionScores = computed(() => {
  if (!props.analysisResult) return {}
  const scores = {}
  dimensionConfig.forEach(dim => {
    scores[dim.id] = Math.floor(Math.random() * 40) + 60 // 模拟分数 60-100
  })
  return scores
})

// 方法
function handleDimensionClick(dimension) {
  selectedDimension.value = dimension.id
  emit('dimension-click', dimension)
}

function isSelected(dimensionId) {
  return selectedDimension.value === dimensionId
}

function getScoreColor(score) {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#eab308'
  return '#ef4444'
}

function toggleTreeNode(nodeId) {
  // 树节点展开/折叠逻辑
  console.log('Toggle tree node:', nodeId)
}
</script>

<template>
  <div class="dimension-matrix">
    <!-- 矩阵可视化 -->
    <div class="matrix-section">
      <h3 class="section-title">三维度分析矩阵</h3>
      <div class="matrix-grid">
        <div
          v-for="dim in dimensionConfig"
          :key="dim.id"
          class="matrix-cell"
          :class="{
            selected: isSelected(dim.id),
            'dimension-transaction': dim.dimension === 'transaction',
            'dimension-communication': dim.dimension === 'communication',
            'dimension-behavior': dim.dimension === 'behavior',
          }"
          @click="handleDimensionClick(dim)"
        >
          <div class="cell-header">
            <span class="cell-icon">{{ dim.icon }}</span>
            <span class="cell-title">{{ dim.title }}</span>
          </div>
          <div class="cell-body">
            <div class="score-display">
              <span
                class="score-value"
                :style="{ color: getScoreColor(dimensionScores[dim.id] || 0) }"
              >
                {{ dimensionScores[dim.id] || '--' }}
              </span>
              <span class="score-label">分</span>
            </div>
            <p class="cell-description">{{ dim.description }}</p>
          </div>
          <div
            v-if="isSelected(dim.id)"
            class="cell-indicator"
          ></div>
        </div>
      </div>
    </div>

    <!-- 决策路径可视化 -->
    <div class="decision-tree-section">
      <h3 class="section-title">决策路径分析</h3>
      <div class="tree-container">
        <div
          v-for="node in decisionTree"
          :key="node.id"
          class="tree-node root-node"
        >
          <div class="node-content">
            <span class="node-label">{{ node.label }}</span>
          </div>
          <div class="node-children">
            <div
              v-for="child in node.children"
              :key="child.id"
              class="tree-node dimension-node"
            >
              <div class="node-content">
                <span class="node-label">{{ child.label }}</span>
                <span
                  v-if="child.score"
                  class="node-score"
                  :style="{ background: getScoreColor(child.score) }"
                >
                  {{ child.score }}
                </span>
              </div>
              <div
                v-if="child.children"
                class="node-children"
              >
                <div
                  v-for="subChild in child.children"
                  :key="subChild.id"
                  class="tree-node leaf-node"
                >
                  <div class="node-content">
                    <span class="node-label">{{ subChild.label }}</span>
                    <span
                      v-if="subChild.score"
                      class="node-score"
                      :style="{ background: getScoreColor(subChild.score) }"
                    >
                      {{ subChild.score }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dimension-matrix {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  margin: 0 0 1rem;
}

/* 矩阵网格 */
.matrix-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.matrix-cell {
  position: relative;
  padding: 1rem;
  background: var(--bg-primary, #fff);
  border: 2px solid var(--border-color, #e2e8f0);
  border-radius: var(--border-radius, 8px);
  cursor: pointer;
  transition: all var(--transition-fast, 150ms ease);
}

.matrix-cell:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
}

.matrix-cell.selected {
  border-color: var(--color-primary, #4f46e5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.matrix-cell.dimension-transaction {
  border-left: 4px solid #3b82f6;
}

.matrix-cell.dimension-communication {
  border-left: 4px solid #8b5cf6;
}

.matrix-cell.dimension-behavior {
  border-left: 4px solid #ec4899;
}

.cell-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.cell-icon {
  font-size: 1.5rem;
}

.cell-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
}

.cell-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.score-display {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
}

.score-value {
  font-size: 1.5rem;
  font-weight: 700;
}

.score-label {
  font-size: 0.875rem;
  color: var(--text-secondary, #64748b);
}

.cell-description {
  font-size: 0.8125rem;
  color: var(--text-secondary, #64748b);
  margin: 0;
  line-height: 1.4;
}

.cell-indicator {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 8px;
  height: 8px;
  background: var(--color-primary, #4f46e5);
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

/* 决策路径树 */
.tree-container {
  background: var(--bg-primary, #fff);
  border-radius: var(--border-radius-lg, 12px);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm, 0 1px 2px 0 rgba(0, 0, 0, 0.05));
}

.tree-node {
  margin-left: 1.5rem;
}

.root-node {
  margin-left: 0;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--bg-secondary, #f8fafc);
  border-radius: var(--border-radius, 8px);
  margin-bottom: 0.5rem;
  border-left: 3px solid var(--color-primary, #4f46e5);
}

.dimension-node .node-content {
  border-left-color: #8b5cf6;
}

.leaf-node .node-content {
  border-left-color: #ec4899;
}

.node-label {
  flex: 1;
  font-size: 0.9375rem;
  color: var(--text-primary, #1e293b);
  font-weight: 500;
}

.node-score {
  padding: 0.25rem 0.625rem;
  background: var(--color-primary, #4f46e5);
  color: white;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.node-children {
  margin-top: 0.5rem;
}

@media (max-width: 1024px) {
  .matrix-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .matrix-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .tree-node {
    margin-left: 1rem;
  }
}

@media (max-width: 640px) {
  .matrix-grid {
    grid-template-columns: 1fr;
  }
}
</style>
