import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import UploadPage from '@/app/(admin)/upload/page'

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8001'

// Real gateway contract: POST /webapp/ingest -> { ok: true } (async pipeline, gap D2).
describe('T5 - Upload', () => {
  it('confirms a file was sent for processing', async () => {
    render(<UploadPage />)
    const file = new File(['dummy'], 'moked_bituach.pdf', { type: 'application/pdf' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, file)
    await waitFor(() => expect(screen.getByText('נשלח לעיבוד')).toBeInTheDocument())
    expect(screen.getByText('moked_bituach.pdf')).toBeInTheDocument()
  })

  it('marks a failed upload', async () => {
    server.use(http.post(`${GATEWAY}/webapp/ingest`, () => HttpResponse.json({}, { status: 500 })))
    render(<UploadPage />)
    const file = new File(['dummy'], 'scan_blur.jpg', { type: 'image/jpeg' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, file)
    await waitFor(() => expect(screen.getByText('נכשל')).toBeInTheDocument())
  })
})
