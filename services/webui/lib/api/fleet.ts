import { z } from 'zod'
import { KpiRawSchema, ReviewItemSchema } from './schemas'

const BASE = process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'

async function get<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`Fleet API ${path}: ${res.status}`)
  return schema.parse(await res.json())
}

async function put(path: string, body: unknown): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Fleet API PUT ${path}: ${res.status}`)
}

export const fetchKpis = () => get('/kpis', KpiRawSchema)
export const fetchConfig = () => get('/config', z.record(z.string(), z.unknown()))
export const updateConfig = (key: string, value: unknown) => put(`/config/${key}`, { value })
export const fetchReviewQueue = () => get('/review-queue', z.array(ReviewItemSchema))
export const resolveReviewItem = (id: string, action: 'accept' | 'reject', payload?: unknown) =>
  put(`/review-queue/${id}/${action}`, payload ?? {})
