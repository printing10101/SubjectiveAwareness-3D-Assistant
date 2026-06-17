import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'

import BaseSkeleton from '../../src/components/ui/BaseSkeleton.vue'

describe('BaseSkeleton', () => {
  it('renders text type by default', () => {
    const wrapper = mount(BaseSkeleton)
    expect(wrapper.find('.skeleton-text').exists()).toBe(true)
  })

  it('renders correct number of rows for text type', () => {
    const wrapper = mount(BaseSkeleton, {
      props: { type: 'text', rows: 5 },
    })
    expect(wrapper.findAll('.skeleton-line').length).toBe(5)
  })

  it('renders card type', () => {
    const wrapper = mount(BaseSkeleton, {
      props: { type: 'card' },
    })
    expect(wrapper.find('.skeleton-card').exists()).toBe(true)
  })

  it('renders avatar in card type when enabled', () => {
    const wrapper = mount(BaseSkeleton, {
      props: { type: 'card', avatar: true },
    })
    expect(wrapper.find('.skeleton-avatar').exists()).toBe(true)
  })

  it('hides avatar in card type when disabled', () => {
    const wrapper = mount(BaseSkeleton, {
      props: { type: 'card', avatar: false },
    })
    expect(wrapper.find('.skeleton-avatar').exists()).toBe(false)
  })

  it('renders list type', () => {
    const wrapper = mount(BaseSkeleton, {
      props: { type: 'list', rows: 3 },
    })
    expect(wrapper.findAll('.skeleton-list-item').length).toBe(3)
  })

  it('renders table type', () => {
    const wrapper = mount(BaseSkeleton, {
      props: { type: 'table', rows: 4 },
    })
    expect(wrapper.find('.skeleton-table-header').exists()).toBe(true)
    expect(wrapper.findAll('.skeleton-table-row').length).toBe(4)
  })

  it('applies animation class when animated', () => {
    const wrapper = mount(BaseSkeleton, {
      props: { animated: true },
    })
    expect(wrapper.find('.skeleton-animated').exists()).toBe(true)
  })

  it('removes animation class when not animated', () => {
    const wrapper = mount(BaseSkeleton, {
      props: { animated: false },
    })
    expect(wrapper.find('.skeleton-animated').exists()).toBe(false)
  })

  it('validates type prop', () => {
    const validator = BaseSkeleton.props.type.validator
    expect(validator('text')).toBe(true)
    expect(validator('card')).toBe(true)
    expect(validator('list')).toBe(true)
    expect(validator('table')).toBe(true)
    expect(validator('invalid')).toBe(false)
  })

  it('has default rows value of 3', () => {
    const wrapper = mount(BaseSkeleton)
    expect(wrapper.props('rows')).toBe(3)
  })

  it('has default animated value of true', () => {
    const wrapper = mount(BaseSkeleton)
    expect(wrapper.props('animated')).toBe(true)
  })
})
