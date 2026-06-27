import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('next-auth', () => ({ getServerSession: vi.fn() }))
vi.mock('next/headers', () => ({ cookies: vi.fn() }))
vi.mock('@/lib/auth', () => ({ authOptions: {} }))

import { POST } from '@/app/api/accident-upload/route'
import { getServerSession } from 'next-auth'
import { cookies } from 'next/headers'

// The handler only reads req.formData(); a minimal stub avoids jsdom multipart parsing.
function makeRequest() {
  const fd = new FormData()
  fd.append('file', new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' }))
  return { method: 'POST', formData: async () => fd }
}

describe('accident-upload route injects the caller context', () => {
  beforeEach(() => vi.clearAllMocks())

  it('forwards X-Caller-Context resolved from the session to /files', async () => {
    vi.mocked(getServerSession).mockResolvedValue({ user: { role: 'company_admin', company_id: 'co1' } } as never)
    vi.mocked(cookies).mockResolvedValue({ get: () => undefined } as never)
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ file_url: 'https://drive/x' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const res = await POST(makeRequest() as never)
    expect(res.status).toBe(200)
    expect(await res.json()).toEqual({ file_url: 'https://drive/x' })

    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>
    expect(JSON.parse(headers['X-Caller-Context'])).toEqual({ role: 'company_admin', company_id: 'co1' })
    expect(headers['X-Internal-Token']).toBeDefined()
  })

  it('scopes a system admin to the active company from the switcher cookie', async () => {
    vi.mocked(getServerSession).mockResolvedValue({ user: { role: 'admin', company_id: null } } as never)
    vi.mocked(cookies).mockResolvedValue({ get: () => ({ value: 'co5' }) } as never)
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ file_url: 'u' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await POST(makeRequest() as never)
    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>
    expect(JSON.parse(headers['X-Caller-Context'])).toEqual({ role: 'admin', company_id: 'co5' })
  })

  it('rejects an unauthenticated request', async () => {
    vi.mocked(getServerSession).mockResolvedValue(null as never)
    const res = await POST(makeRequest() as never)
    expect(res.status).toBe(401)
  })
})
