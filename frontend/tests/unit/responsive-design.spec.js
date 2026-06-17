/**
 * 响应式设计验证测试
 * 测试三个分辨率：320px（移动端）、768px（平板）、1280px（桌面）
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

// 导入新组件
import StandardPathBadge from '../../src/components/analysis/StandardPathBadge.vue'
import MultiSubjectPanel from '../../src/components/analysis/MultiSubjectPanel.vue'
import EvidenceLayerPanel from '../../src/components/analysis/EvidenceLayerPanel.vue'
import BoundaryAlertBanner from '../../src/components/analysis/BoundaryAlertBanner.vue'
import ReportView from '../../src/views/ReportView.vue'

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

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
})

// 设置视口宽度的辅助函数
function setViewportWidth(width) {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  })
  
  Object.defineProperty(document.documentElement, 'clientWidth', {
    writable: true,
    configurable: true,
    value: width,
  })
  
  // 触发 resize 事件
  window.dispatchEvent(new Event('resize'))
}

// 检查是否有横向滚动条
function hasHorizontalScrollbar() {
  return document.documentElement.scrollWidth > document.documentElement.clientWidth
}

// 创建路由实例
function createMockRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/report', component: { template: '<div>Report</div>' } },
    ],
  })
}

describe('响应式设计验证', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('320px 移动端分辨率', () => {
    beforeEach(() => {
      setViewportWidth(320)
    })

    it('StandardPathBadge 在 320px 下正常显示', () => {
      const wrapper = mount(StandardPathBadge, {
        props: {
          pathType: 'direct-evidence',
          label: '直接证据',
          description: '描述文本',
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.standard-path-badge').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('MultiSubjectPanel 在 320px 下正常显示', () => {
      const wrapper = mount(MultiSubjectPanel, {
        props: {
          subjects: [
            { id: 1, name: '主体1', role: '主犯', description: '描述' },
            { id: 2, name: '主体2', role: '从犯', description: '描述' },
          ],
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.multi-subject-panel').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('EvidenceLayerPanel 在 320px 下正常显示', () => {
      const wrapper = mount(EvidenceLayerPanel, {
        props: {
          evidenceLayers: {
            layer1: { items: [{ title: '证据1', content: '内容' }] },
            layer2: { items: [{ title: '证据2', content: '内容' }] },
          },
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.evidence-layer-panel').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('BoundaryAlertBanner 在 320px 下正常显示', () => {
      const wrapper = mount(BoundaryAlertBanner, {
        props: {
          alerts: [
            { type: 'warning', title: '警告', message: '警告信息' },
          ],
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.boundary-alert-banner').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('ReportView 在 320px 下不出现横向滚动条', async () => {
      const router = createMockRouter()
      
      const wrapper = mount(ReportView, {
        global: {
          plugins: [router],
          stubs: {
            'router-link': true,
            'router-view': true,
          },
        },
      })
      
      await router.isReady()
      
      expect(wrapper.exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })
  })

  describe('768px 平板分辨率', () => {
    beforeEach(() => {
      setViewportWidth(768)
    })

    it('StandardPathBadge 在 768px 下正常显示', () => {
      const wrapper = mount(StandardPathBadge, {
        props: {
          pathType: 'direct-evidence',
          label: '直接证据',
          description: '描述文本',
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.standard-path-badge').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('MultiSubjectPanel 在 768px 下正常显示', () => {
      const wrapper = mount(MultiSubjectPanel, {
        props: {
          subjects: [
            { id: 1, name: '主体1', role: '主犯', description: '描述' },
            { id: 2, name: '主体2', role: '从犯', description: '描述' },
          ],
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.multi-subject-panel').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('EvidenceLayerPanel 在 768px 下正常显示', () => {
      const wrapper = mount(EvidenceLayerPanel, {
        props: {
          evidenceLayers: {
            layer1: { items: [{ title: '证据1', content: '内容' }] },
            layer2: { items: [{ title: '证据2', content: '内容' }] },
          },
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.evidence-layer-panel').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('BoundaryAlertBanner 在 768px 下正常显示', () => {
      const wrapper = mount(BoundaryAlertBanner, {
        props: {
          alerts: [
            { type: 'warning', title: '警告', message: '警告信息' },
          ],
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.boundary-alert-banner').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('ReportView 在 768px 下正常显示', async () => {
      const router = createMockRouter()
      
      const wrapper = mount(ReportView, {
        global: {
          plugins: [router],
          stubs: {
            'router-link': true,
            'router-view': true,
          },
        },
      })
      
      await router.isReady()
      
      expect(wrapper.exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })
  })

  describe('1280px 桌面分辨率', () => {
    beforeEach(() => {
      setViewportWidth(1280)
    })

    it('StandardPathBadge 在 1280px 下正常显示', () => {
      const wrapper = mount(StandardPathBadge, {
        props: {
          pathType: 'direct-evidence',
          label: '直接证据',
          description: '描述文本',
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.standard-path-badge').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('MultiSubjectPanel 在 1280px 下正常显示', () => {
      const wrapper = mount(MultiSubjectPanel, {
        props: {
          subjects: [
            { id: 1, name: '主体1', role: '主犯', description: '描述' },
            { id: 2, name: '主体2', role: '从犯', description: '描述' },
          ],
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.multi-subject-panel').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('EvidenceLayerPanel 在 1280px 下正常显示', () => {
      const wrapper = mount(EvidenceLayerPanel, {
        props: {
          evidenceLayers: {
            layer1: { items: [{ title: '证据1', content: '内容' }] },
            layer2: { items: [{ title: '证据2', content: '内容' }] },
          },
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.evidence-layer-panel').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('BoundaryAlertBanner 在 1280px 下正常显示', () => {
      const wrapper = mount(BoundaryAlertBanner, {
        props: {
          alerts: [
            { type: 'warning', title: '警告', message: '警告信息' },
          ],
        },
      })
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.boundary-alert-banner').exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })

    it('ReportView 在 1280px 下正常显示', async () => {
      const router = createMockRouter()
      
      const wrapper = mount(ReportView, {
        global: {
          plugins: [router],
          stubs: {
            'router-link': true,
            'router-view': true,
          },
        },
      })
      
      await router.isReady()
      
      expect(wrapper.exists()).toBe(true)
      expect(hasHorizontalScrollbar()).toBe(false)
    })
  })

  describe('响应式布局验证', () => {
    it('所有组件在三个分辨率下都能正确渲染', () => {
      const resolutions = [320, 768, 1280]
      
      for (const width of resolutions) {
        setViewportWidth(width)
        
        const badge = mount(StandardPathBadge, {
          props: {
            pathType: 'direct-evidence',
            label: '直接证据',
            description: '描述',
          },
        })
        expect(badge.exists()).toBe(true)
        
        const panel = mount(MultiSubjectPanel, {
          props: {
            subjects: [{ id: 1, name: '主体', role: '角色', description: '描述' }],
          },
        })
        expect(panel.exists()).toBe(true)
        
        const evidence = mount(EvidenceLayerPanel, {
          props: {
            evidenceLayers: {
              layer1: { items: [{ title: '证据1', content: '内容' }] },
            },
          },
        })
        expect(evidence.exists()).toBe(true)
        
        const alert = mount(BoundaryAlertBanner, {
          props: {
            alerts: [{ type: 'warning', title: '警告', message: '警告信息' }],
          },
        })
        expect(alert.exists()).toBe(true)
      }
    })

    it('移动端 320px 下不出现横向滚动条', async () => {
      setViewportWidth(320)
      
      const router = createMockRouter()
      
      const wrapper = mount(ReportView, {
        global: {
          plugins: [router],
          stubs: {
            'router-link': true,
            'router-view': true,
          },
        },
      })
      
      await router.isReady()
      
      expect(hasHorizontalScrollbar()).toBe(false)
    })
  })
})
