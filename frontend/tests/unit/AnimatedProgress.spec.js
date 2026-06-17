import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'

import AnimatedProgress from '../../src/components/ui/AnimatedProgress.vue'

describe('AnimatedProgress', () => {
  it('renders with default value', () => {
    const wrapper = mount(AnimatedProgress)
    expect(wrapper.find('.progress-track').exists()).toBe(true)
  })

  it('renders with custom value', () => {
    const wrapper = mount(AnimatedProgress, {
      props: { value: 75 },
    })
    expect(wrapper.props('value')).toBe(75)
  })

  it('validates value is between 0 and 100', () => {
    const validator = AnimatedProgress.props.value.validator
    expect(validator(0)).toBe(true)
    expect(validator(50)).toBe(true)
    expect(validator(100)).toBe(true)
    expect(validator(-1)).toBe(false)
    expect(validator(101)).toBe(false)
  })

  it('applies custom duration', () => {
    const wrapper = mount(AnimatedProgress, {
      props: { value: 50, duration: 800 },
    })
    expect(wrapper.props('duration')).toBe(800)
  })

  it('applies custom color', () => {
    const wrapper = mount(AnimatedProgress, {
      props: { value: 50, color: '#FF9500' },
    })
    const fill = wrapper.find('.progress-fill')
    expect(fill.attributes('style')).toContain('background')
  })

  it('shows percentage text when enabled', () => {
    const wrapper = mount(AnimatedProgress, {
      props: { value: 75, showLabel: true },
    })
    expect(wrapper.text()).toContain('75%')
  })

  it('hides percentage text when disabled', () => {
    const wrapper = mount(AnimatedProgress, {
      props: { value: 75, showLabel: false },
    })
    expect(wrapper.text()).not.toContain('%')
  })

  it('applies custom height', () => {
    const wrapper = mount(AnimatedProgress, {
      props: { value: 50, height: '12px' },
    })
    expect(wrapper.props('height')).toBe('12px')
  })

  it('applies rounded style by default', () => {
    const wrapper = mount(AnimatedProgress, {
      props: { value: 50 },
    })
    expect(wrapper.props('rounded')).toBe(true)
  })
})
