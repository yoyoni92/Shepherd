// Real contract: services/langgraph-agent POST /agent/run
//   body  { query, caller_context }
//   reply { answer, tools_used, reasoning_steps }
// No citation list (gap D1) — tools_used surfaces what the agent touched.
// Browser → same-origin proxy (app/api/proxy/agent); tests point straight at the agent host.
const BASE = process.env.NEXT_PUBLIC_AGENT_BASE ?? '/api/proxy/agent'

export interface AgentReply {
  content: string
  citations: string[]
  tool_calls: string[]
}

export async function chatWithAgent(message: string, _sessionId: string): Promise<AgentReply> {
  const res = await fetch(`${BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: message, caller_context: { role: 'admin' } }),
  })
  if (!res.ok) throw new Error(`Agent: ${res.status}`)
  const data = (await res.json()) as { answer: string; tools_used?: string[]; reasoning_steps?: string[] }
  return { content: data.answer, citations: [], tool_calls: data.tools_used ?? [] }
}
