'use client'
import { useSession } from 'next-auth/react'
import { ChatPanel } from '@/components/ChatPanel'
import { useFleetChat } from '@/hooks/useFleetChat'

export default function ChatPage() {
  const { data: session } = useSession()
  const sessionId = session?.user?.email ?? 'admin'
  const { messages, loading, send } = useFleetChat(sessionId)
  return (
    <div>
      <h2 className="text-[15px] font-bold mb-4">Fleet Chat</h2>
      <ChatPanel
        messages={messages}
        loading={loading}
        onSend={send}
        header="◆ Fleet Q&A + Actions · RAG + LangGraph + Fleet API · ownership-scoped"
        placeholder="Ask about a vehicle, or give a command..."
      />
      <p className="text-[10.5px] text-muted mt-2">
        Data questions and actions route to RAG / LangGraph / Fleet API; results are filtered to the caller&apos;s vehicles (admin sees all).
      </p>
    </div>
  )
}
