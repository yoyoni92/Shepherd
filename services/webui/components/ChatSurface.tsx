'use client'
import { useEffect, useRef, useState } from 'react'
import { Send, FileText } from 'lucide-react'

export interface ChatMsg {
  role: 'user' | 'assistant'
  content: string
  citations?: string[]
}

interface ChatSurfaceProps {
  messages: ChatMsg[]
  loading: boolean
  onSend: (text: string) => void
  placeholder: string
}

export function ChatSurface({ messages, loading, onSend, placeholder }: ChatSurfaceProps) {
  const [draft, setDraft] = useState('')
  const bodyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const send = () => {
    const v = draft.trim()
    if (!v) return
    onSend(v)
    setDraft('')
  }

  return (
    <div className="bg-panel border border-line rounded-[14px] flex flex-col" style={{ height: 480 }}>
      <div ref={bodyRef} className="flex-1 overflow-y-auto flex flex-col gap-4" style={{ padding: '20px 22px' }}>
        {messages.map((m, i) => {
          const user = m.role === 'user'
          return (
            <div key={i} className="flex" style={{ justifyContent: user ? 'flex-start' : 'flex-end' }}>
              <div
                style={{
                  maxWidth: '78%',
                  padding: '13px 16px',
                  borderRadius: user ? '14px 14px 14px 4px' : '14px 14px 4px 14px',
                  background: user ? 'linear-gradient(135deg,#3b82f6,#2563eb)' : 'var(--panel2)',
                  border: user ? 'none' : '1px solid var(--control)',
                  color: user ? '#fff' : 'var(--ink)',
                }}
              >
                <div className="text-[13.5px] whitespace-pre-wrap" style={{ lineHeight: 1.6 }}>
                  {m.content}
                </div>
                {m.citations && m.citations.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2.5 pt-2.5 border-t border-control">
                    {m.citations.map((c) => (
                      <span
                        key={c}
                        className="inline-flex items-center gap-[5px] text-[10.5px] font-semibold rounded-md ltr"
                        style={{ background: 'var(--chip)', border: '1px solid var(--control)', color: 'var(--accent)', padding: '3px 8px' }}
                      >
                        <FileText size={11} />
                        {c}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        })}
        {loading && <div className="self-end text-xs text-faint animate-pulse">…</div>}
      </div>
      <div className="flex gap-2.5 items-end border-t border-line" style={{ padding: '14px 16px' }}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder={placeholder}
          className="flex-1 bg-bg border border-control rounded-[10px] text-sm text-ink outline-none focus:border-accent"
          style={{ padding: '12px 14px' }}
        />
        <button
          onClick={send}
          aria-label="שלח"
          className="rounded-[10px] flex items-center justify-center text-white cursor-pointer"
          style={{ width: 44, height: 44, background: 'linear-gradient(135deg,#3b82f6,#1d4ed8)' }}
        >
          <Send size={19} style={{ transform: 'scaleX(-1)' }} />
        </button>
      </div>
    </div>
  )
}
