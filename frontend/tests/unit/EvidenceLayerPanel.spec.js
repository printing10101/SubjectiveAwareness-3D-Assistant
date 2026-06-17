import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import EvidenceLayerPanel from '../../src/components/analysis/EvidenceLayerPanel.vue'

describe('EvidenceLayerPanel', () => {
  const mockEvidenceLayers = {
    layer1: {
      items: [
        { type: '书证', title: '银行流水', content: '显示异常转账', source: '公安机关', relevance: '高' }
      ]
    },
    layer2: {
      items: [
        { type: '电子数据', title: '聊天记录', content: '涉及犯罪沟通' },
        { type: '监控视频', title: 'ATM监控', content: '取款画面' }
      ]
    },
    layer3: { items: [] },
    layer4: { items: [] }
  }

  it('renders correctly with evidence data', () => {
    const wrapper = mount(EvidenceLayerPanel, {
      props: { evidenceLayers: mockEvidenceLayers }
    })
    expect(wrapper.text()).toContain('证据分层展示')
  })

  it('does not render when no evidence provided', () => {
    const wrapper = mount(EvidenceLayerPanel, {
      props: { evidenceLayers: {} }
    })
    expect(wrapper.find('.evidence-layer-panel').exists()).toBe(false)
  })

  it('renders four tab buttons', () => {
    const wrapper = mount(EvidenceLayerPanel, {
      props: { evidenceLayers: mockEvidenceLayers }
    })
    const tabs = wrapper.findAll('.tab-button')
    expect(tabs.length).toBe(4)
  })

  it('shows correct badge counts on tabs', () => {
    const wrapper = mount(EvidenceLayerPanel, {
      props: { evidenceLayers: mockEvidenceLayers }
    })
    const badges = wrapper.findAll('.tab-badge')
    // layer1 has 1 item, layer2 has 2 items, layer3 and layer4 have 0 (no badge)
    expect(badges.length).toBe(2)
    expect(badges[0].text()).toBe('1')
    expect(badges[1].text()).toBe('2')
  })

  it('defaults to layer1 tab', () => {
    const wrapper = mount(EvidenceLayerPanel, {
      props: { evidenceLayers: mockEvidenceLayers }
    })
    const firstTab = wrapper.findAll('.tab-button')[0]
    expect(firstTab.classes()).toContain('active')
  })

  it('switches tab on click', async () => {
    const wrapper = mount(EvidenceLayerPanel, {
      props: { evidenceLayers: mockEvidenceLayers }
    })
    const tabs = wrapper.findAll('.tab-button')
    await tabs[1].trigger('click')
    expect(tabs[1].classes()).toContain('active')
  })

  it('displays evidence items for active layer', () => {
    const wrapper = mount(EvidenceLayerPanel, {
      props: { evidenceLayers: mockEvidenceLayers }
    })
    expect(wrapper.text()).toContain('银行流水')
  })

  it('shows empty state when layer has no items', async () => {
    const wrapper = mount(EvidenceLayerPanel, {
      props: { evidenceLayers: mockEvidenceLayers }
    })
    const tabs = wrapper.findAll('.tab-button')
    await tabs[2].trigger('click') // layer3 has empty items
    expect(wrapper.text()).toContain('暂无证据')
  })

  it('displays evidence source and relevance', () => {
    const wrapper = mount(EvidenceLayerPanel, {
      props: { evidenceLayers: mockEvidenceLayers }
    })
    expect(wrapper.text()).toContain('来源')
    expect(wrapper.text()).toContain('公安机关')
    expect(wrapper.text()).toContain('关联性')
  })
})
