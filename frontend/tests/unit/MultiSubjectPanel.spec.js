import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import MultiSubjectPanel from '../../src/components/analysis/MultiSubjectPanel.vue'

describe('MultiSubjectPanel', () => {
  const mockSubjects = [
    {
      id: '1',
      name: '张三',
      role: '主犯',
      description: '负责技术支持',
      evidence: '银行流水记录',
      analysis: '参与程度较深'
    },
    {
      id: '2',
      name: '李四',
      role: '从犯',
      description: '提供账户'
    }
  ]

  it('renders correctly with subjects', () => {
    const wrapper = mount(MultiSubjectPanel, {
      props: {
        subjects: mockSubjects
      }
    })
    expect(wrapper.text()).toContain('涉案主体列表')
    expect(wrapper.text()).toContain('2 人')
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('李四')
  })

  it('does not render when no subjects provided', () => {
    const wrapper = mount(MultiSubjectPanel, {
      props: {
        subjects: []
      }
    })
    expect(wrapper.find('.multi-subject-panel').exists()).toBe(false)
  })

  it('displays subject role when provided', () => {
    const wrapper = mount(MultiSubjectPanel, {
      props: {
        subjects: mockSubjects
      }
    })
    expect(wrapper.text()).toContain('主犯')
    expect(wrapper.text()).toContain('从犯')
  })

  it('expands subject card on click', async () => {
    const wrapper = mount(MultiSubjectPanel, {
      props: {
        subjects: mockSubjects
      }
    })
    
    // Initially, content should not be visible
    expect(wrapper.find('.card-content').exists()).toBe(false)
    
    // Click the first card header
    const cardHeader = wrapper.find('.card-header')
    await cardHeader.trigger('click')
    
    // Now content should be visible
    expect(wrapper.find('.card-content').exists()).toBe(true)
    expect(wrapper.text()).toContain('负责技术支持')
  })

  it('collapses subject card on second click', async () => {
    const wrapper = mount(MultiSubjectPanel, {
      props: {
        subjects: mockSubjects
      }
    })
    
    const cardHeader = wrapper.find('.card-header')
    
    // First click - expand
    await cardHeader.trigger('click')
    expect(wrapper.find('.card-content').exists()).toBe(true)
    
    // Second click - collapse
    await cardHeader.trigger('click')
    expect(wrapper.find('.card-content').exists()).toBe(false)
  })

  it('displays evidence when available', async () => {
    const wrapper = mount(MultiSubjectPanel, {
      props: {
        subjects: mockSubjects
      }
    })
    
    const cardHeader = wrapper.find('.card-header')
    await cardHeader.trigger('click')
    
    expect(wrapper.text()).toContain('关联证据')
    expect(wrapper.text()).toContain('银行流水记录')
  })

  it('displays analysis when available', async () => {
    const wrapper = mount(MultiSubjectPanel, {
      props: {
        subjects: mockSubjects
      }
    })
    
    const cardHeader = wrapper.find('.card-header')
    await cardHeader.trigger('click')
    
    expect(wrapper.text()).toContain('分析说明')
    expect(wrapper.text()).toContain('参与程度较深')
  })

  it('rotates expand icon when expanded', async () => {
    const wrapper = mount(MultiSubjectPanel, {
      props: {
        subjects: mockSubjects
      }
    })
    
    const expandIcon = wrapper.find('.expand-icon')
    expect(expandIcon.classes()).not.toContain('rotated')
    
    const cardHeader = wrapper.find('.card-header')
    await cardHeader.trigger('click')
    
    expect(expandIcon.classes()).toContain('rotated')
  })
})
