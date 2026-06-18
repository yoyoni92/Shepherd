import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './msw/server'
import UploadPage from '@/app/(admin)/upload/page'

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8001'

describe('T5 - Upload', () => {
  it('shows classification result after file submit', async () => {
    render(<UploadPage />)
    const file = new File(['dummy'], 'moked_bituach.pdf', { type: 'application/pdf' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, file)
    await waitFor(() => expect(screen.getByText('insurance_cert')).toBeInTheDocument())
    expect(screen.getByText('insurance_valid_to updated')).toBeInTheDocument()
  })

  it('surfaces low-confidence upload in review (flagged)', async () => {
    server.use(
      http.post(`${GATEWAY}/ingest/webapp`, () =>
        HttpResponse.json({ doc_type: 'uncertain', confidence: 0.48, status: 'sent to review', flagged: true }),
      ),
    )
    render(<UploadPage />)
    const file = new File(['dummy'], 'scan_blur.jpg', { type: 'image/jpeg' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, file)
    await waitFor(() => expect(screen.getByText('sent to review')).toBeInTheDocument())
  })
})
