import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import AnimatedNumber from '../../src/components/ui/AnimatedNumber.vue'

describe('AnimatedNumber', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    // mock requestAnimationFrame
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => setTimeout(cb, 16))
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((id) => {
      clearTimeout(id)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('renders with default value', () => {
    const wrapper = mount(AnimatedNumber, {
      props: { value: 100 },
    })
    expect(wrapper.text()).toContain('0')
  })

  it('renders with custom initial value', () => {
    const wrapper = mount(AnimatedNumber, {
      props: { value: 100, initialValue: 50 },
    })
    expect(wrapper.text()).toContain('50')
  })

  it('formats integer values correctly', () => {
    const wrapper = mount(AnimatedNumber, {
      props: { value: 1234, decimals: 0 },
    })
    expect(wrapper.text()).toContain('0')
  })

  it('formats decimal values correctly', () => {
    const wrapper = mount(AnimatedNumber, {
      props: { value: 95.67, decimals: 2, initialValue: 95.67 },
    })
    expect(wrapper.text()).toContain('95.67')
  })

  it('applies custom duration', () => {
    const wrapper = mount(AnimatedNumber, {
      props: { value: 100, duration: 1000 },
    })
    expect(wrapper.props('duration')).toBe(1000)
  })

  it('renders as span element', () => {
    const wrapper = mount(AnimatedNumber, {
      props: { value: 100 },
    })
    expect(wrapper.element.tagName).toBe('SPAN')
  })

  it('validates decimals prop', () => {
    const wrapper = mount(AnimatedNumber, {
      props: { value: 100, decimals: 2 },
    })
    expect(wrapper.props('decimals')).toBe(2)
  })

  it('validates duration prop is positive', () => {
    const wrapper = mount(AnimatedNumber, {
      props: { value: 100, duration: 600 },
    })
    expect(wrapper.props('duration')).toBeGreaterThan(0)
  })

  it('cleans up animation on unmount', async () => {
    const wrapper = mount(AnimatedNumber, {
      props: { value: 100 },
    })
    wrapper.unmount()
    // Should not throw errors after unmount
    expect(cancelAnimationFrame).toHaveBeenCalled()
  })
})
