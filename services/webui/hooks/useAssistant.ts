'use client'
// ponytail: no fleet/agent/gateway imports - ESLint enforces this at hooks/useAssistant.ts
import { useState, useCallback } from 'react'

const ASSISTANT_URL = process.env.NEXT_PUBLIC_ASSISTANT_URL ?? 'http://localhost:8006'

export interface AssistantMessage {
  role: 'user' | 'assistant'
  content: string
}

export function useAssistant() {
  const [messages, setMessages] = useState<AssistantMessage[]>([])
  const [loading, setLoading] = useState(false)

  const send = useCallback(async (text: string) => {
    setMessages(m => [...m, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await fetch(`${ASSISTANT_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()
      setMessages(m => [...m, { role: 'assistant', content: data.content ?? data.message ?? '' }])
    } finally {
      setLoading(false)
    }
  }, [])

  return { messages, loading, send }
}
