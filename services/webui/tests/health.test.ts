import { describe, it, expect } from 'vitest'
import { summarizeHealth, downCount, type ServiceHealth } from '@/lib/health'

const svc = (key: string, status: 'up' | 'down'): ServiceHealth => ({ key, status, latencyMs: status === 'up' ? 12 : null })

describe('summarizeHealth', () => {
  it('is ok when every service is up', () => {
    expect(summarizeHealth([svc('a', 'up'), svc('b', 'up')])).toBe('ok')
  })
  it('is degraded when some are down', () => {
    expect(summarizeHealth([svc('a', 'up'), svc('b', 'down')])).toBe('degraded')
  })
  it('is down when all are down or the list is empty', () => {
    expect(summarizeHealth([svc('a', 'down')])).toBe('down')
    expect(summarizeHealth([])).toBe('down')
  })
})

describe('downCount', () => {
  it('counts only down services', () => {
    expect(downCount([svc('a', 'up'), svc('b', 'down'), svc('c', 'down')])).toBe(2)
  })
})
