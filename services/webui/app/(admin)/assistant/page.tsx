'use client'
import { ChatPanel } from '@/components/ChatPanel'
import { useAssistant } from '@/hooks/useAssistant'

export default function AssistantPage() {
  const { messages, loading, send } = useAssistant()
  return (
    <div>
      <h2 className="text-[15px] font-bold mb-4">Assistant</h2>
      <ChatPanel
        messages={messages}
        loading={loading}
        onSend={send}
        header="✦ Moshes · your fleet assistant · Ollama (Llama 3) · DB-blind, local"
        placeholder="Ask a general fleet question..."
      />
      <p className="text-[10.5px] text-muted mt-2">
        The assistant is grounded as a fleet helper, refuses off-topic, invents no prices/legal advice, and never queries the database.
      </p>
    </div>
  )
}
