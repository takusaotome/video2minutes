import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { PrimeVueToastSymbol } from 'primevue/usetoast'

describe('FileUploader - Simple Test', () => {
  let pinia
  let wrapper

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)

    // Mock the stores and services
    vi.doMock('@/stores/tasks', () => ({
      useTasksStore: () => ({
        uploadFile: vi.fn(),
        tasks: []
      })
    }))
  })

  it('can mount the component', async () => {
    // Dynamic import after mocks
    const FileUploader = (await import('@/components/FileUploader.vue')).default

    const mockToast = {
      add: vi.fn(),
      removeGroup: vi.fn(),
      removeAllGroups: vi.fn(),
      clear: vi.fn()
    }

    wrapper = mount(FileUploader, {
      global: {
        plugins: [pinia],
        provide: {
          [PrimeVueToastSymbol]: mockToast,
          PrimeVueToast: mockToast
        },
        stubs: {
          Card: true,
          FileUpload: true,
          Button: true,
          ProgressBar: true,
          Badge: true
        }
      }
    })

    expect(wrapper.exists()).toBe(true)
  })
})
