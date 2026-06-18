import { UploadResultSchema, type UploadResult } from './schemas'

const BASE = process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8001'

export async function uploadDocument(file: File): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/ingest/webapp`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Gateway upload: ${res.status}`)
  return UploadResultSchema.parse(await res.json())
}
