'use client'
import { useRef, useEffect } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  citations?: string[]
  tool_calls?: string[]
}

interface ChatPanelProps {
  messages: Message[]
  loading: boolean
  onSend: (text: string) => void
  header: string
  placeholder: string
}

export function ChatPanel({ messages, loading, onSend, header, placeholder }: ChatPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const val = inputRef.current?.value.trim()
    if (!val) return
    onSend(val)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="flex flex-col bg-panel border border-line rounded-xl" style={{ height: 560 }}>
      <div className="px-4 py-3 border-b border-line text-xs text-slate-400">{header}</div>
      <div ref={bodyRef} className="flex-1 overflow-auto p-4 flex flex-col gap-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[74%] px-3 py-2 rounded-xl text-[12.5px] leading-relaxed ${
              m.role === 'user'
                ? 'self-end bg-blue-950 border border-blue-900 text-blue-100 rounded-br-sm'
                : 'self-start bg-panel2 border border-line rounded-bl-sm text-slate-200'
            }`}
          >
            {m.content}
            {m.citations?.length ? (
              <div className="mt-1.5 text-[10px] text-emerald-400 border-t border-dashed border-line pt-1">
                {m.citations.join(' · ')}
              </div>
            ) : null}
            {m.tool_calls?.length ? (
              <div className="mt-1.5 text-[10px] text-violet-400">{m.tool_calls.join(' · ')}</div>
            ) : null}
          </div>
        ))}
        {loading && <div className="self-start text-xs text-muted animate-pulse">...</div>}
      </div>
      <div className="p-3 border-t border-line flex gap-2">
        <input
          ref={inputRef}
          placeholder={placeholder}
          className="flex-1 bg-panel2 border border-line rounded-lg px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500"
          onKeyDown={e => e.key === 'Enter' && handleSend()}
        />
        <button
          onClick={handleSend}
          className="bg-blue-600 text-white border-none rounded-lg px-4 font-bold cursor-pointer hover:brightness-110"
        >
          Send
        </button>
      </div>
    </div>
  )
}
