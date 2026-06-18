import { renderHook, act, waitFor } from '@testing-library/react'
import { it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useAssistant } from '@/hooks/useAssistant'

const FLEET = process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'
const RAG = process.env.NEXT_PUBLIC_RAG_URL ?? 'http://localhost:8004'

// T4: assistant must NEVER hit Fleet API or RAG (DB-blind contract)
it('T4 - never hits Fleet API or RAG', async () => {
  let fleetHit = false
  let ragHit = false
  server.use(
    http.all(`${FLEET}/*`, () => { fleetHit = true; return HttpResponse.json({}) }),
    http.all(`${RAG}/*`, () => { ragHit = true; return HttpResponse.json({}) }),
  )

  const { result } = renderHook(() => useAssistant())
  await act(async () => { await result.current.send('How often should fleet tires be rotated?') })
  await waitFor(() => expect(result.current.messages).toHaveLength(2))

  expect(fleetHit).toBe(false)
  expect(ragHit).toBe(false)
})

it('T4 - returns assistant response content', async () => {
  const { result } = renderHook(() => useAssistant())
  await act(async () => { await result.current.send('How often should fleet tires be rotated?') })
  await waitFor(() => expect(result.current.messages).toHaveLength(2))
  expect(result.current.messages[1].content).toMatch(/8,000|rotate/i)
})
