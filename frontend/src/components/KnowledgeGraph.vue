<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

import * as d3 from 'd3'

const props = defineProps({
  nodes: {
    type: Array,
    default: () => [],
  },
  edges: {
    type: Array,
    default: () => [],
  },
  mode: {
    type: String,
    default: 'full',
    validator: (v) => ['mini', 'full'].includes(v),
  },
  onNodeClick: {
    type: Function,
    default: null,
  },
  showEdgeLabels: {
    type: Boolean,
    default: false,
  },
  highlightedNodeIds: {
    type: Array,
    default: () => [],
  },
  centerNodeId: {
    type: [Number, String, null],
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['node-click', 'ready'])

const containerRef = ref(null)
const svgRef = ref(null)

const isFullscreen = ref(false)
let simulation = null
let zoom = null
let gContainer = null
let svg = null

const LINE_STYLE_MAP = {
  solid: '',
  dashed: '8,4',
  dotted: '2,4',
  dotdash: '8,4,2,4',
}

function initGraph() {
  if (!containerRef.value) return

  svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()

  const container = containerRef.value
  const width = container.clientWidth
  const height = container.clientHeight

  svg.attr('width', width).attr('height', height)

  zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      gContainer.attr('transform', event.transform)
    })

  svg.call(zoom)

  gContainer = svg.append('g')

  const defs = svg.append('defs')
  const markerTypes = [
    { id: 'arrow-solid', color: '#9CA3AF', width: 6, height: 4 },
    { id: 'arrow-dashed', color: '#F59E0B', width: 6, height: 4 },
    { id: 'arrow-dotted', color: '#EF4444', width: 6, height: 4 },
    { id: 'arrow-highlight', color: '#8B5CF6', width: 8, height: 6 },
  ]

  markerTypes.forEach((m) => {
    defs
      .append('marker')
      .attr('id', m.id)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', m.width)
      .attr('markerHeight', m.height)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', m.color)
      .attr('opacity', 0.6)
  })

  renderGraph()
}

function renderGraph() {
  if (!gContainer || !props.nodes.length) return

  const nodesData = props.nodes.map((n) => ({ ...n }))
  const edgesData = props.edges.map((e) => ({ ...e }))
  const nodeIdMap = new Map(nodesData.map((n) => [n.id, n]))
  const validEdges = edgesData.filter(
    (e) => nodeIdMap.has(e.source) && nodeIdMap.has(e.target)
  )

  const edgeLineGroup = gContainer.append('g').attr('class', 'edges')
  const edgeLabelGroup = gContainer.append('g').attr('class', 'edge-labels')
  const nodeGroup = gContainer.append('g').attr('class', 'nodes')
  const labelGroup = gContainer.append('g').attr('class', 'node-labels')

  const linkElements = edgeLineGroup
    .selectAll('line')
    .data(validEdges)
    .enter()
    .append('line')
    .attr('stroke', (d) => getEdgeColor(d.type))
    .attr('stroke-width', 1.2)
    .attr('stroke-opacity', 0.45)
    .attr('stroke-dasharray', (d) => LINE_STYLE_MAP[d.lineStyle] || '')
    .attr('marker-end', (d) => `url(#arrow-${d.lineStyle || 'solid'})`)

  const edgeLabels = edgeLabelGroup
    .selectAll('text')
    .data(props.showEdgeLabels ? validEdges : [])
    .enter()
    .append('text')
    .text((d) => d.label || '')
    .attr('font-size', 9)
    .attr('fill', '#9CA3AF')
    .attr('text-anchor', 'middle')
    .attr('dy', -4)
    .style('pointer-events', 'none')
    .style('opacity', 0)

  const nodeElements = nodeGroup
    .selectAll('g')
    .data(nodesData)
    .enter()
    .append('g')
    .attr('class', 'node')
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      handleNodeClick(d)
    })

  nodeElements
    .append('circle')
    .attr('r', (d) => (d.size || 10) * 0.7)
    .attr('fill', (d) => d.color || '#6B7280')
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 2)
    .attr('stroke-opacity', 0.8)

  nodeElements
    .append('circle')
    .attr('r', (d) => d.size || 10)
    .attr('fill', 'none')
    .attr('stroke', (d) => d.color || '#6B7280')
    .attr('stroke-width', 2)
    .attr('stroke-opacity', 0.3)
    .style('transition', 'stroke-opacity 0.3s ease')

  const nodeLabels = labelGroup
    .selectAll('text')
    .data(nodesData)
    .enter()
    .append('text')
    .text((d) => truncateLabel(d.label || d.id, 18))
    .attr('font-size', props.mode === 'mini' ? 9 : 10)
    .attr('fill', '#374151')
    .attr('text-anchor', 'middle')
    .attr('dy', (d) => (d.size || 10) + 12)
    .style('pointer-events', 'none')
    .style('user-select', 'none')
    .style('font-weight', 500)

  nodeElements
    .on('mouseenter', function () {
      d3.select(this).select('circle:first-child').transition().duration(200).attr('r', function () {
        const baseR = d3.select(this.parentNode).datum().size || 10
        return baseR * 0.85
      })
      d3.select(this).select('circle:last-child').transition().duration(200).attr('stroke-opacity', 0.7)
    })
    .on('mouseleave', function () {
      d3.select(this).select('circle:first-child').transition().duration(200).attr('r', function () {
        const baseR = d3.select(this.parentNode).datum().size || 10
        return baseR * 0.7
      })
      d3.select(this).select('circle:last-child').transition().duration(200).attr('stroke-opacity', 0.3)
    })

  simulation = d3
    .forceSimulation(nodesData)
    .force(
      'link',
      d3
        .forceLink(validEdges)
        .id((d) => d.id)
        .distance(120)
    )
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(0, 0))
    .force('collision', d3.forceCollide().radius((d) => (d.size || 10) + 16))
    .alphaDecay(0.02)

  simulation.on('tick', () => {
    linkElements
      .attr('x1', (d) => d.source.x)
      .attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x)
      .attr('y2', (d) => d.target.y)

    nodeElements.attr('transform', (d) => `translate(${d.x},${d.y})`)

    if (props.showEdgeLabels) {
      edgeLabels
        .attr('x', (d) => (d.source.x + d.target.x) / 2)
        .attr('y', (d) => (d.source.y + d.target.y) / 2)
    }

    nodeLabels.attr('x', (d) => d.x).attr('y', (d) => d.y)
  })

  const dragHandler = d3
    .drag()
    .on('start', (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x
      d.fy = d.y
    })
    .on('drag', (event, d) => {
      d.fx = event.x
      d.fy = event.y
    })
    .on('end', (event, d) => {
      if (!event.active) simulation.alphaTarget(0)
      d.fx = null
      d.fy = null
    })

  nodeElements.call(dragHandler)

  if (props.centerNodeId && nodesData.length > 0) {
    const centerNode = nodesData.find((n) => n.id === props.centerNodeId)
    if (centerNode) {
      centerNode.fx = 0
      centerNode.fy = 0
    }
  }

  simulation.on('end', () => {
    edgeLabels.style('opacity', 1)
  })

  emit('ready')
}

function truncateLabel(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? `${text.substring(0, maxLen - 1)  }...` : text
}

function getEdgeColor(type) {
  const colorMap = {
    references: '#9CA3AF',
    contradicts: '#EF4444',
    supersedes: '#F59E0B',
    extends: '#10B981',
    depends_on: '#3B82F6',
  }
  return colorMap[type] || '#9CA3AF'
}

function handleNodeClick(node) {
  if (props.onNodeClick) {
    props.onNodeClick(node)
  }
  emit('node-click', node)
}

function highlightNodes(nodeIds) {
  if (!gContainer) return
  const nodeIdSet = new Set(nodeIds)
  gContainer.selectAll('.node').each(function (d) {
    const el = d3.select(this)
    if (nodeIds.length === 0) {
      el.style('opacity', 1)
      el.selectAll('circle').attr('stroke', '#ffffff')
    } else if (nodeIdSet.has(d.id)) {
      el.style('opacity', 1)
      el.select('circle:last-child')
        .attr('stroke', '#8B5CF6')
        .attr('stroke-width', 3)
        .attr('stroke-opacity', 0.9)
    } else {
      el.style('opacity', 0.15)
    }
  })
  gContainer.selectAll('.edges line').each(function (d) {
    const el = d3.select(this)
    if (nodeIds.length === 0) {
      el.attr('stroke-opacity', 0.45).attr('stroke-width', 1.2)
    } else if (nodeIdSet.has(d.source.id) && nodeIdSet.has(d.target.id)) {
      el.attr('stroke-opacity', 0.9)
        .attr('stroke-width', 2.5)
        .attr('stroke', '#8B5CF6')
        .attr('marker-end', 'url(#arrow-highlight)')
    } else {
      el.attr('stroke-opacity', 0.05)
    }
  })
}

function centerOnNode(nodeId) {
  if (!svg || !simulation) return
  const nodes = simulation.nodes()
  const targetNode = nodes.find((n) => n.id === nodeId)
  if (!targetNode) return

  const container = containerRef.value
  const width = container.clientWidth
  const height = container.clientHeight

  svg
    .transition()
    .duration(750)
    .call(
      zoom.transform,
      d3.zoomIdentity.translate(width / 2, height / 2).scale(1.3).translate(-targetNode.x, -targetNode.y)
    )
}

function zoomToFit() {
  if (!svg || !gContainer) return
  const container = containerRef.value
  const width = container.clientWidth
  const height = container.clientHeight
  const bounds = gContainer.node().getBBox()
  if (bounds.width === 0 || bounds.height === 0) return

  const dx = bounds.width
  const dy = bounds.height
  const x = bounds.x + dx / 2
  const y = bounds.y + dy / 2
  const scale = Math.min(0.9, 0.9 / Math.max(dx / width, dy / height))
  const translate = [width / 2 - scale * x, height / 2 - scale * y]

  svg
    .transition()
    .duration(750)
    .call(zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale))
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
}

function resetView() {
  if (!svg) return
  svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity)
}

function destroyGraph() {
  if (simulation) {
    simulation.stop()
    simulation = null
  }
  if (svg) {
    svg.selectAll('*').remove()
  }
  zoom = null
  gContainer = null
}

watch(
  () => [props.nodes, props.edges],
  () => {
    nextTick(() => {
      destroyGraph()
      initGraph()
    })
  },
  { deep: true }
)

watch(
  () => props.highlightedNodeIds,
  (newIds) => {
    highlightNodes(newIds || [])
  }
)

onMounted(() => {
  nextTick(() => {
    initGraph()
  })
})

onUnmounted(() => {
  destroyGraph()
})

defineExpose({
  highlightNodes,
  centerOnNode,
  zoomToFit,
  resetView,
  toggleFullscreen,
})
</script>

<template>
  <div
    ref="containerRef"
    class="knowledge-graph"
    :class="{
      'graph--mini': mode === 'mini',
      'graph--full': mode === 'full',
      'graph--fullscreen': isFullscreen,
    }"
  >
    <div v-if="loading" class="graph-state graph-state--loading">
      <div class="graph-spinner"></div>
      <p class="graph-state-text">正在加载知识图谱...</p>
    </div>

    <div v-else-if="error" class="graph-state graph-state--error">
      <div class="graph-error-icon">!</div>
      <h3 class="graph-state-title">加载失败</h3>
      <p class="graph-state-text">{{ error }}</p>
    </div>

    <div v-else-if="!nodes.length" class="graph-state graph-state--empty">
      <div class="graph-empty-icon">
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none">
          <circle
            cx="20"
            cy="22"
            r="8"
            stroke="#D1D5DB"
            stroke-width="2"
            fill="none"/>
          <circle
            cx="44"
            cy="22"
            r="8"
            stroke="#D1D5DB"
            stroke-width="2"
            fill="none"/>
          <circle
            cx="32"
            cy="44"
            r="8"
            stroke="#D1D5DB"
            stroke-width="2"
            fill="none"/>
          <line
            x1="26"
            y1="26"
            x2="38"
            y2="26"
            stroke="#D1D5DB"
            stroke-width="1.5"
            stroke-dasharray="4,2"/>
          <line
            x1="23"
            y1="28"
            x2="29"
            y2="38"
            stroke="#D1D5DB"
            stroke-width="1.5"
            stroke-dasharray="4,2"/>
          <line
            x1="41"
            y1="28"
            x2="35"
            y2="38"
            stroke="#D1D5DB"
            stroke-width="1.5"
            stroke-dasharray="4,2"/>
        </svg>
      </div>
      <h3 class="graph-state-title">暂无图谱数据</h3>
      <p class="graph-state-text">创建知识条目并建立关联关系后，图谱将在此展示</p>
    </div>

    <svg ref="svgRef" class="graph-svg"/>

    <div class="graph-controls">
      <button class="graph-ctrl-btn" title="放大" @click="svg && zoom && svg.transition().duration(300).call(zoom.scaleBy, 1.3)">
        <span>+</span>
      </button>
      <button class="graph-ctrl-btn" title="缩小" @click="svg && zoom && svg.transition().duration(300).call(zoom.scaleBy, 0.7)">
        <span>−</span>
      </button>
      <button class="graph-ctrl-btn" title="重置视图" @click="resetView">
        <span>⟲</span>
      </button>
      <button class="graph-ctrl-btn" title="适应画面" @click="zoomToFit">
        <span>⊞</span>
      </button>
      <button class="graph-ctrl-btn" title="全屏" @click="toggleFullscreen">
        <span>{{ isFullscreen ? '⤢' : '⤡' }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.knowledge-graph {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: var(--bg-primary, #ffffff);
  border-radius: var(--border-radius, 8px);
  overflow: hidden;
  border: 1px solid var(--border-color, #e5e7eb);
}

.graph--mini {
  min-height: 280px;
  max-height: 400px;
}

.graph--fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  border-radius: 0;
  border: none;
  min-height: 100vh;
  max-height: 100vh;
}

.graph-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.graph-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  background: rgba(255, 255, 255, 0.95);
  gap: 0.75rem;
  padding: 2rem;
}

.graph-state--loading {
  background: rgba(255, 255, 255, 0.92);
}

.graph-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color, #e5e7eb);
  border-top-color: var(--color-primary, #4F46E5);
  border-radius: 50%;
  animation: graph-spin 0.8s linear infinite;
}

@keyframes graph-spin {
  to { transform: rotate(360deg); }
}

.graph-error-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: #fef2f2;
  border: 2px solid #fecaca;
  color: #dc2626;
  border-radius: 50%;
  font-size: 1.5rem;
  font-weight: 700;
}

.graph-empty-icon {
  opacity: 0.5;
}

.graph-state-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #111827);
  margin: 0;
}

.graph-state-text {
  font-size: 0.9rem;
  color: var(--text-secondary, #6b7280);
  margin: 0;
  text-align: center;
  max-width: 320px;
}

.graph-controls {
  position: absolute;
  right: 12px;
  bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 20;
}

.graph-ctrl-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary, #ffffff);
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  font-family: inherit;
  color: var(--text-secondary, #6b7280);
  transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.graph-ctrl-btn:hover {
  background: var(--bg-tertiary, #f3f4f6);
  color: var(--text-primary, #111827);
  border-color: var(--color-primary, #4F46E5);
}
</style>