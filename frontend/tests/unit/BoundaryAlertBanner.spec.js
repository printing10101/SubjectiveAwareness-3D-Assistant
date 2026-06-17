import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import BoundaryAlertBanner from '../../src/components/analysis/BoundaryAlertBanner.vue'

describe('BoundaryAlertBanner', () => {
  const mockAlerts = [
    { type: 'warning', message: '警告信息', title: '警告标题' },
    { type: 'error', message: '错误信息', title: '错误标题' },
    { type: 'info', message: '提示信息', title: '提示标题' }
  ]

  it('renders correctly with alerts', () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: mockAlerts }
    })
    expect(wrapper.find('.boundary-alert-banner').exists()).toBe(true)
    expect(wrapper.findAll('.alert-item').length).toBe(3)
  })

  it('does not render when no alerts provided', () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: [] }
    })
    expect(wrapper.find('.boundary-alert-banner').exists()).toBe(false)
  })

  it('displays alert message and title', () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: mockAlerts }
    })
    expect(wrapper.text()).toContain('警告信息')
    expect(wrapper.text()).toContain('警告标题')
    expect(wrapper.text()).toContain('错误信息')
    expect(wrapper.text()).toContain('提示信息')
  })

  it('applies correct inline style for warning', () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: [mockAlerts[0]] }
    })
    const alertItem = wrapper.find('.alert-item')
    expect(alertItem.attributes('style')).toContain('background-color')
  })

  it('applies correct inline style for error', () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: [mockAlerts[1]] }
    })
    const alertItem = wrapper.find('.alert-item')
    expect(alertItem.attributes('style')).toContain('background-color')
  })

  it('applies correct inline style for info', () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: [mockAlerts[2]] }
    })
    const alertItem = wrapper.find('.alert-item')
    expect(alertItem.attributes('style')).toContain('background-color')
  })

  it('shows dismiss button when dismissible is true', () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: mockAlerts, dismissible: true }
    })
    const dismissButtons = wrapper.findAll('.dismiss-button')
    expect(dismissButtons.length).toBe(3)
  })

  it('hides dismiss button when dismissible is false', () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: mockAlerts, dismissible: false }
    })
    expect(wrapper.find('.dismiss-button').exists()).toBe(false)
  })

  it('emits dismiss event when dismiss button clicked', async () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: mockAlerts, dismissible: true }
    })
    const dismissButton = wrapper.find('.dismiss-button')
    await dismissButton.trigger('click')
    expect(wrapper.emitted('dismiss')).toBeTruthy()
    expect(wrapper.emitted('dismiss')[0]).toEqual([0])
  })

  it('displays correct icon for each alert type', () => {
    const wrapper = mount(BoundaryAlertBanner, {
      props: { alerts: mockAlerts }
    })
    const icons = wrapper.findAll('.alert-icon')
    expect(icons[0].text()).toContain('⚠️')
    expect(icons[1].text()).toContain('❌')
    expect(icons[2].text()).toContain('ℹ️')
  })
})
