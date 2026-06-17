import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'

const mockPush = vi.fn()
const mockLocalStorage = (() => {
  let store = {}
  return {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value
    }),
    clear: vi.fn(() => {
      store = {}
    }),
  }
})()

Object.defineProperty(globalThis, 'localStorage', {
  value: mockLocalStorage,
})

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useRoute: () => ({
    name: 'welcome',
  }),
}))

import WelcomeView from '../../src/views/WelcomeView.vue'

describe('WelcomeView', () => {
  beforeEach(() => {
    mockPush.mockClear()
    mockLocalStorage.clear()
    mockLocalStorage.getItem.mockClear()
    mockLocalStorage.setItem.mockClear()
  })

  it('renders the welcome title correctly', () => {
    const wrapper = mount(WelcomeView)
    expect(wrapper.text()).toContain('帮信罪辅助裁定系统')
  })

  it('renders the subtitle', () => {
    const wrapper = mount(WelcomeView)
    expect(wrapper.text()).toContain('AI驱动的法律分析工具')
  })

  it('renders the start button', () => {
    const wrapper = mount(WelcomeView)
    const button = wrapper.find('.start-btn')
    expect(button.exists()).toBe(true)
    expect(button.text()).toContain('开始使用')
  })

  it('renders the analyze new case button', () => {
    const wrapper = mount(WelcomeView)
    const button = wrapper.find('.action-card.primary')
    expect(button.exists()).toBe(true)
    expect(button.text()).toContain('分析新案件')
  })

  it('sets localStorage and navigates on start button click', async () => {
    const wrapper = mount(WelcomeView)
    const button = wrapper.find('.start-btn')
    await button.trigger('click')
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('hasVisitedWelcome', 'true')
    expect(mockPush).toHaveBeenCalledWith('/main')
  })

  it('navigates to /main on mount if already visited', () => {
    mockLocalStorage.getItem.mockReturnValueOnce('true')
    mount(WelcomeView)
    expect(mockPush).toHaveBeenCalledWith('/main')
  })
})
