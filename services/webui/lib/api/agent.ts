const BASE = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8003'

export async function chatWithAgent(
  message: string,
  session_id: string,
): Promise<{ content: string; citations: string[]; tool_calls: string[] }> {
  const res = await fetch(`${BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id }),
  })
  if (!res.ok) throw new Error(`Agent: ${res.status}`)
  return res.json()
}
