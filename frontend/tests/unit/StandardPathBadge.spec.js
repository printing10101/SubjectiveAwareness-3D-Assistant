import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import StandardPathBadge from '../../src/components/analysis/StandardPathBadge.vue'

describe('StandardPathBadge', () => {
  it('renders correctly with direct-evidence path type', () => {
    const wrapper = mount(StandardPathBadge, {
      props: {
        pathType: 'direct-evidence',
        label: '测试标签',
        description: '测试描述'
      }
    })
    expect(wrapper.text()).toContain('测试标签')
    expect(wrapper.text()).toContain('测试描述')
    expect(wrapper.text()).toContain('直接证据路径')
  })

  it('renders correctly with objective-anomaly path type', () => {
    const wrapper = mount(StandardPathBadge, {
      props: {
        pathType: 'objective-anomaly',
        label: '异常标签'
      }
    })
    expect(wrapper.text()).toContain('异常标签')
    expect(wrapper.text()).toContain('客观异常路径')
  })

  it('renders correctly with behavior-pattern path type', () => {
    const wrapper = mount(StandardPathBadge, {
      props: {
        pathType: 'behavior-pattern',
        label: '行为标签'
      }
    })
    expect(wrapper.text()).toContain('行为标签')
    expect(wrapper.text()).toContain('行为模式路径')
  })

  it('renders correctly with supplementary path type', () => {
    const wrapper = mount(StandardPathBadge, {
      props: {
        pathType: 'supplementary',
        label: '补充标签'
      }
    })
    expect(wrapper.text()).toContain('补充标签')
    expect(wrapper.text()).toContain('补充审查路径')
  })

  it('applies correct styles for direct-evidence path', () => {
    const wrapper = mount(StandardPathBadge, {
      props: {
        pathType: 'direct-evidence',
        label: '测试'
      }
    })
    const badge = wrapper.find('.standard-path-badge')
    expect(badge.exists()).toBe(true)
    const style = badge.attributes('style')
    expect(style).toContain('color: rgb(34, 197, 94)')
  })

  it('hides description when not provided', () => {
    const wrapper = mount(StandardPathBadge, {
      props: {
        pathType: 'direct-evidence',
        label: '测试标签'
      }
    })
    expect(wrapper.find('.badge-description').exists()).toBe(false)
  })

  it('shows description when provided', () => {
    const wrapper = mount(StandardPathBadge, {
      props: {
        pathType: 'direct-evidence',
        label: '测试标签',
        description: '详细描述'
      }
    })
    expect(wrapper.find('.badge-description').exists()).toBe(true)
    expect(wrapper.text()).toContain('详细描述')
  })

  it('renders icon correctly', () => {
    const wrapper = mount(StandardPathBadge, {
      props: {
        pathType: 'direct-evidence',
        label: '测试'
      }
    })
    const icon = wrapper.find('.badge-icon')
    expect(icon.exists()).toBe(true)
    expect(icon.text()).toBe('✓')
  })
})
