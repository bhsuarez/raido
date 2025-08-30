import '@testing-library/jest-dom'

// Mock react-hot-toast to avoid DOM side effects in tests
vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

