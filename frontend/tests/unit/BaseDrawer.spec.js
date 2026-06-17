import { mount } from '@vue/test-utils'
import { describe, it, expect, afterEach } from 'vitest'

import BaseDrawer from '../../src/components/ui/BaseDrawer.vue'

describe('BaseDrawer', () => {
  // 清理 Teleport 到 body 的 DOM 元素
  afterEach(() => {
    document.body.querySelectorAll('.base-drawer-overlay').forEach(el => el.remove())
  })

  it('renders when visible', () => {
    const wrapper = mount(BaseDrawer, {
      props: { visible: true },
      attachTo: document.body,
    })
    expect(document.querySelector('.base-drawer')).toBeTruthy()
    wrapper.unmount()
  })

  it('does not render when hidden', () => {
    const wrapper = mount(BaseDrawer, {
      props: { visible: false },
      attachTo: document.body,
    })
    expect(document.querySelector('.base-drawer')).toBeFalsy()
    wrapper.unmount()
  })

  it('applies custom direction', () => {
    const wrapper = mount(BaseDrawer, {
      props: { visible: true, direction: 'left' },
      attachTo: document.body,
    })
    expect(document.querySelector('.drawer-left')).toBeTruthy()
    wrapper.unmount()
  })

  it('applies custom width for right direction', () => {
    const wrapper = mount(BaseDrawer, {
      props: { visible: true, direction: 'right', width: '400px' },
      attachTo: document.body,
    })
    const drawer = document.querySelector('.base-drawer')
    expect(drawer.style.width).toBe('400px')
    wrapper.unmount()
  })

  it('shows overlay when enabled', () => {
    const wrapper = mount(BaseDrawer, {
      props: { visible: true, showOverlay: true },
      attachTo: document.body,
    })
    const overlay = document.querySelector('.base-drawer-overlay')
    expect(overlay).toBeTruthy()
    expect(overlay.classList.contains('has-overlay')).toBe(true)
    wrapper.unmount()
  })

  it('emits close and update:visible when close button clicked', async () => {
    const wrapper = mount(BaseDrawer, {
      props: { visible: true, showClose: true },
      attachTo: document.body,
    })
    const closeBtn = document.querySelector('.drawer-close')
    await closeBtn.click()
    expect(wrapper.emitted('close')).toBeTruthy()
    expect(wrapper.emitted('update:visible')).toBeTruthy()
    expect(wrapper.emitted('update:visible')[0]).toEqual([false])
    wrapper.unmount()
  })

  it('renders title when provided', () => {
    const wrapper = mount(BaseDrawer, {
      props: { visible: true, title: '测试标题' },
      attachTo: document.body,
    })
    const title = document.querySelector('.drawer-title')
    expect(title.textContent).toContain('测试标题')
    wrapper.unmount()
  })

  it('validates direction prop', () => {
    const validator = BaseDrawer.props.direction.validator
    expect(validator('left')).toBe(true)
    expect(validator('right')).toBe(true)
    expect(validator('top')).toBe(true)
    expect(validator('bottom')).toBe(true)
    expect(validator('invalid')).toBe(false)
  })
})
