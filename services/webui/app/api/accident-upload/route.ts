import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { cookies } from 'next/headers'
import { authOptions } from '@/lib/auth'
import { buildCallerContext } from '@/lib/callerContext'
import { randomUUID } from 'crypto'

// Server-only Fleet API base (never exposed to the browser); Fleet owns storage.
const FLEET_BASE = process.env.FLEET_API_URL ?? process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'
const INTERNAL_TOKEN = process.env.INTERNAL_SERVICE_TOKEN ?? ''

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const form = await req.formData()
  const file = form.get('file') as File | null
  if (!file) return NextResponse.json({ error: 'no file' }, { status: 400 })

  const key = `accidents/${randomUUID()}/${file.name}`
  const upload = new FormData()
  upload.append('key', key)
  upload.append('file', file, file.name)

  // /files now resolves the target company from the caller context (per-tenant Drive).
  const active = (await cookies()).get('active_company_id')?.value
  const callerContext = buildCallerContext(session.user, active)

  const res = await fetch(`${FLEET_BASE}/files`, {
    method: 'POST',
    headers: { 'X-Internal-Token': INTERNAL_TOKEN, 'X-Caller-Context': callerContext },
    body: upload,
    cache: 'no-store',
  })
  if (!res.ok) return NextResponse.json({ error: 'upload failed' }, { status: 502 })

  const { file_url } = await res.json()
  return NextResponse.json({ file_url })
}
