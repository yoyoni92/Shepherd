import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import { useCompanySettings } from '@/hooks/useCompanySettings'
import { QueryClientWrapper } from './helpers'

const FLEET = 'http://localhost:8000'

describe('useCompanySettings', () => {
  it('reads settings with credentials redacted to gdrive_configured', async () => {
    const { result } = renderHook(() => useCompanySettings('co1'), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.settings).toBeDefined())
    expect(result.current.settings).toMatchObject({ gdrive_configured: true, feature_flags: { attendance: false } })
    // The raw credentials blob is never present in a read.
    expect(Object.keys(result.current.settings!)).not.toContain('gdrive_credentials_json')
  })

  it('does not fetch when no company is selected', async () => {
    const { result } = renderHook(() => useCompanySettings(null), { wrapper: QueryClientWrapper })
    expect(result.current.settings).toBeUndefined()
    expect(result.current.loading).toBe(false)
  })

  it('saves folder + credentials + attendance flag', async () => {
    let body: Record<string, unknown> | null = null
    server.use(
      http.patch(`${FLEET}/companies/:id/settings`, async ({ params, request }) => {
        body = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({
          company_id: params.id,
          gdrive_folder_id: (body.gdrive_folder_id as string) ?? null,
          gdrive_configured: true,
          feature_flags: (body.feature_flags as Record<string, unknown>) ?? {},
        })
      }),
    )
    const { result } = renderHook(() => useCompanySettings('co1'), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.settings).toBeDefined())
    await act(async () => {
      await result.current.save({
        gdrive_folder_id: 'new-folder',
        gdrive_credentials_json: '{"type":"service_account"}',
        feature_flags: { attendance: true },
      })
    })
    expect(body).toEqual({
      gdrive_folder_id: 'new-folder',
      gdrive_credentials_json: '{"type":"service_account"}',
      feature_flags: { attendance: true },
    })
  })

  it('surfaces the server validation message on a 400', async () => {
    server.use(
      http.patch(`${FLEET}/companies/:id/settings`, () =>
        HttpResponse.json({ detail: 'Drive folder not accessible: 404' }, { status: 400 }),
      ),
    )
    const { result } = renderHook(() => useCompanySettings('co1'), { wrapper: QueryClientWrapper })
    await waitFor(() => expect(result.current.settings).toBeDefined())
    await expect(result.current.save({ gdrive_folder_id: 'bad' })).rejects.toThrow('Drive folder not accessible: 404')
  })
})
