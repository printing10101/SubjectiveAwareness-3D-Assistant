import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock IntersectionObserver
class MockIntersectionObserver {
  constructor() {
    this.observe = vi.fn()
    this.unobserve = vi.fn()
    this.disconnect = vi.fn()
  }
}

Object.defineProperty(window, 'IntersectionObserver', {
  value: MockIntersectionObserver,
  writable: true,
})

const mockPush = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useRoute: () => ({
    name: 'report',
    params: { id: 'test-id' },
  }),
}))

vi.mock('../../src/stores/analysisStore.js', () => ({
  useAnalysisStore: () => ({
    currentAnalysis: {
      id: 'test-id',
      caseText: '测试案件文本',
      result: {
        standardPaths: [
          { pathType: 'direct-evidence', label: '直接证据', description: '描述' }
        ],
        subjects: [
          { id: '1', name: '张三', role: '主犯' }
        ],
        evidenceLayers: {
          layer1: { items: [{ title: '证据1' }] },
          layer2: { items: [] },
          layer3: { items: [] },
          layer4: { items: [] }
        },
        boundaryAlerts: [
          { type: 'warning', message: '警告信息' }
        ]
      },
      status: 'completed'
    },
    isLoading: false,
    error: null,
    analysisResult: {
      standardPaths: [
        { pathType: 'direct-evidence', label: '直接证据', description: '描述' }
      ],
      subjects: [
        { id: '1', name: '张三', role: '主犯' }
      ],
      evidenceLayers: {
        layer1: { items: [{ title: '证据1' }] },
        layer2: { items: [] },
        layer3: { items: [] },
        layer4: { items: [] }
      },
      boundaryAlerts: [
        { type: 'warning', message: '警告信息' }
      ]
    },
    fetchAnalysis: vi.fn(),
  }),
}))

import ReportView from '../../src/views/ReportView.vue'

describe('ReportView', () => {
  beforeEach(() => {
    mockPush.mockClear()
  })

  it('renders the report view', () => {
    const wrapper = mount(ReportView)
    expect(wrapper.exists()).toBe(true)
  })

  it('does not display score-related content', () => {
    const wrapper = mount(ReportView)
    const text = wrapper.text()
    expect(text).not.toContain('score')
    expect(text).not.toContain('分数')
    expect(text).not.toContain('置信度')
    expect(text).not.toContain('confidence')
  })

  it('renders StandardPathBadge component when data exists', () => {
    const wrapper = mount(ReportView)
    expect(wrapper.find('.standard-paths-section').exists()).toBe(true)
  })

  it('renders MultiSubjectPanel component when data exists', () => {
    const wrapper = mount(ReportView)
    expect(wrapper.findComponent({ name: 'MultiSubjectPanel' }).exists()).toBe(true)
  })

  it('renders EvidenceLayerPanel component when data exists', () => {
    const wrapper = mount(ReportView)
    expect(wrapper.findComponent({ name: 'EvidenceLayerPanel' }).exists()).toBe(true)
  })

  it('renders BoundaryAlertBanner component when data exists', () => {
    const wrapper = mount(ReportView)
    expect(wrapper.findComponent({ name: 'BoundaryAlertBanner' }).exists()).toBe(true)
  })

  it('renders case text section', () => {
    const wrapper = mount(ReportView)
    // 页面显示"事实摘要"而非"案件文本"
    expect(wrapper.text()).toContain('事实摘要')
  })

  it('renders analysis result section', () => {
    const wrapper = mount(ReportView)
    // 页面显示"维度分析"等章节而非"分析结果"
    expect(wrapper.text()).toContain('维度分析')
  })
})
