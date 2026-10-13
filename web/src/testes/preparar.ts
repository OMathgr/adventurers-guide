import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// O React Flow (quadros) mede os nós com ResizeObserver, que o jsdom não tem.
class ResizeObserverDeTeste {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverDeTeste as unknown as typeof ResizeObserver

afterEach(() => {
  cleanup()
  localStorage.clear()
})
