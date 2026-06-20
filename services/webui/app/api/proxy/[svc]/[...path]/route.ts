import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

// Server-only base URLs for the private services (never exposed to the browser).
// Unlike the Fleet proxy, these need no internal token / caller context.
const BASES: Record<string, string | undefined> = {
  agent: process.env.AGENT_URL,
  rag: process.env.RAG_URL,
  gateway: process.env.GATEWAY_URL,
  assistant: process.env.ASSISTANT_URL,
}

async function forward(req: NextRequest, svc: string, path: string[]) {
  const session = await getServerSession(authOptions)
  if (!session) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const base = BASES[svc]
  if (!base) return NextResponse.json({ error: `unknown service: ${svc}` }, { status: 404 })

  const url = `${base}/${path.join('/')}${req.nextUrl.search}`
  const headers: Record<string, string> = {}
  const contentType = req.headers.get('content-type')
  if (contentType) headers['Content-Type'] = contentType

  const hasBody = req.method !== 'GET' && req.method !== 'DELETE'
  const res = await fetch(url, {
    method: req.method,
    headers,
    body: hasBody ? await req.text() : undefined,
    cache: 'no-store',
  })

  const text = await res.text()
  return new NextResponse(text || null, {
    status: res.status,
    headers: { 'content-type': res.headers.get('content-type') ?? 'application/json' },
  })
}

type Ctx = { params: Promise<{ svc: string; path: string[] }> }
const handler = async (req: NextRequest, { params }: Ctx) => {
  const { svc, path } = await params
  return forward(req, svc, path)
}

export const GET = handler
export const POST = handler
export const PUT = handler
export const PATCH = handler
export const DELETE = handler
