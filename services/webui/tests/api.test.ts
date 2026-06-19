import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { fetchVehicles, updateConfig } from '@/lib/api/fleet'
import { chatWithAgent } from '@/lib/api/agent'
import { uploadDocument } from '@/lib/api/gateway'

const FLEET = process.env.NEXT_PUBLIC_FLEET_BASE ?? 'http://localhost:8000'
const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8003'
const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8001'
const ASSISTANT = process.env.NEXT_PUBLIC_ASSISTANT_URL ?? 'http://localhost:8006'

describe('API client error paths', () => {
  it('fetchVehicles throws on non-ok response', async () => {
    server.use(http.get(`${FLEET}/vehicles`, () => HttpResponse.json({}, { status: 500 })))
    await expect(fetchVehicles()).rejects.toThrow('Fleet API /vehicles: 500')
  })

  it('updateConfig throws on non-ok response', async () => {
    server.use(http.put(`${FLEET}/config/:key`, () => HttpResponse.json({}, { status: 403 })))
    await expect(updateConfig('x', 1)).rejects.toThrow('Fleet API PUT /config/x: 403')
  })

  it('chatWithAgent throws on non-ok response', async () => {
    server.use(http.post(`${AGENT}/agent/run`, () => HttpResponse.json({}, { status: 503 })))
    await expect(chatWithAgent('hi', 's1')).rejects.toThrow('Agent: 503')
  })

  it('uploadDocument throws on non-ok response', async () => {
    server.use(http.post(`${GATEWAY}/webapp/ingest`, () => HttpResponse.json({}, { status: 413 })))
    await expect(uploadDocument(new File(['x'], 'x.pdf'), 'admin')).rejects.toThrow('Gateway upload: 413')
  })

  it('useAssistant falls back to data.message when content absent', async () => {
    // covers the `data.message ?? ''` branch in useAssistant
    const { renderHook, act, waitFor } = await import('@testing-library/react')
    const { useAssistant } = await import('@/hooks/useAssistant')
    server.use(http.post(`${ASSISTANT}/chat`, () => HttpResponse.json({ message: 'fallback text' })))
    const { result } = renderHook(() => useAssistant())
    await act(async () => { await result.current.send('hi') })
    await waitFor(() => expect(result.current.messages).toHaveLength(2))
    expect(result.current.messages[1].content).toBe('fallback text')
  })
})
