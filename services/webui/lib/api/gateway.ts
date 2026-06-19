// Real contract: services/channel-gateway POST /webapp/ingest (multipart)
//   fields phone(required), display_name?, text?, file?
//   reply  { ok: true }
// The ingest pipeline is async — no synchronous classification result (gap D2).
const BASE = process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8001'

export async function uploadDocument(file: File, phone: string): Promise<{ ok: boolean }> {
  const form = new FormData()
  form.append('phone', phone)
  form.append('file', file)
  const res = await fetch(`${BASE}/webapp/ingest`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Gateway upload: ${res.status}`)
  return res.json()
}
