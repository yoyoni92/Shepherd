import { z } from 'zod'

export const KpiRawSchema = z.object({
  total_vehicles: z.number(),
  active_drivers: z.number(),
  docs_expiring_soon: z.number(),
  open_events: z.number(),
  unpaid_tickets: z.number(),
  maintenance_due: z.number(),
})

export const ChatResponseSchema = z.object({
  content: z.string(),
  citations: z.array(z.string()).default([]),
  tool_calls: z.array(z.string()).default([]),
})

export const UploadResultSchema = z.object({
  doc_type: z.string(),
  confidence: z.number(),
  plate: z.string().optional(),
  status: z.string(),
  flagged: z.boolean(),
})

export const ReviewItemSchema = z.object({
  id: z.string(),
  file_name: z.string(),
  reason: z.enum(['low_confidence', 'plate_mismatch', 'output_blocked']),
  doc_type: z.string().optional(),
  confidence: z.number().optional(),
  message: z.string(),
})

export type KpiRaw = z.infer<typeof KpiRawSchema>
export type ReviewItem = z.infer<typeof ReviewItemSchema>
export type UploadResult = z.infer<typeof UploadResultSchema>
