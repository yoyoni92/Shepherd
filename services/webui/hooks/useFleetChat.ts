'use client'
import { useState, useCallback } from 'react'
import { chatWithAgent } from '@/lib/api/agent'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  citations?: string[]
  tool_calls?: string[]
}

export function useFleetChat(sessionId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)

  const send = useCallback(async (text: string) => {
    setMessages(m => [...m, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await chatWithAgent(text, sessionId)
      setMessages(m => [...m, {
        role: 'assistant',
        content: res.content,
        citations: res.citations,
        tool_calls: res.tool_calls,
      }])
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  return { messages, loading, send }
}
