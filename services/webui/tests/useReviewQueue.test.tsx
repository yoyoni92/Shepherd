import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { useReviewQueue } from '@/hooks/useReviewQueue'
import { QueryClientWrapper } from './helpers'
import { server } from './msw/server'

const FLEET = process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'

describe('T7 - useReviewQueue', () => {
  it('fetches flagged items', async () => {
    const { result } = renderHook(() => useReviewQueue(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.items.length).toBeGreaterThan(0))
    expect(result.current.items[0].file_name).toBe('scan_blur.jpg')
  })

  it('optimistically removes item on accept', async () => {
    const { result } = renderHook(() => useReviewQueue(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.items).toHaveLength(2))
    // Prime refetch handler BEFORE resolving so onSettled refetch also returns 1 item
    server.use(
      http.get(`${FLEET}/review-queue`, () =>
        HttpResponse.json([
          { id: '2', file_name: 'doc_99x.pdf', reason: 'plate_mismatch', message: 'Plate not in fleet.' },
        ]),
      ),
    )
    act(() => { result.current.resolve({ id: '1', action: 'accept' }) })
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    expect(result.current.items[0].id).toBe('2')
  })

  it('optimistically removes item on reject', async () => {
    const { result } = renderHook(() => useReviewQueue(), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.items).toHaveLength(2))
    server.use(
      http.get(`${FLEET}/review-queue`, () =>
        HttpResponse.json([
          { id: '1', file_name: 'scan_blur.jpg', reason: 'low_confidence', confidence: 0.48, message: 'Low confidence.', doc_type: 'uncertain' },
        ]),
      ),
    )
    act(() => { result.current.resolve({ id: '2', action: 'reject' }) })
    await waitFor(() => expect(result.current.items).toHaveLength(1))
    expect(result.current.items[0].id).toBe('1')
  })
})
