'use client'
import { useSession } from 'next-auth/react'
import { Navigation, CircleHelp, Info } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ChatSurface } from '@/components/ChatSurface'
import { useFleetChat } from '@/hooks/useFleetChat'
import { useAssistant } from '@/hooks/useAssistant'

export default function ChatPage() {
  const { data: session } = useSession()
  const sessionId = session?.user?.email ?? 'admin'
  const fleet = useFleetChat(sessionId)
  const assistant = useAssistant()

  return (
    <div className="animate-fade-up mx-auto" style={{ maxWidth: 900 }}>
      <Tabs defaultValue="fleet">
        <TabsList className="mb-4">
          <TabsTrigger value="fleet">
            <Navigation size={15} />
            שאילתות צי <span className="text-[10px] opacity-70">RAG</span>
          </TabsTrigger>
          <TabsTrigger value="assistant">
            <CircleHelp size={15} />
            עוזר כללי <span className="text-[10px] opacity-70">Ollama</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="fleet">
          <NoteBanner
            color="#7dd3fc"
            bg="rgba(56,189,248,.07)"
            border="#16344f"
            text="מחובר לנתוני הצי דרך Fleet API · התשובות כוללות מקורות"
          />
          <ChatSurface
            messages={fleet.messages}
            loading={fleet.loading}
            onSend={fleet.send}
            placeholder="שאל על רכבים, נהגים, מסמכים…"
          />
        </TabsContent>

        <TabsContent value="assistant">
          <NoteBanner
            color="#c4b5fd"
            bg="rgba(167,139,250,.07)"
            border="#2e2257"
            text="עוזר מקומי (Ollama) ללא גישה למסד הנתונים · לשאלות כלליות בלבד"
          />
          <ChatSurface
            messages={assistant.messages}
            loading={assistant.loading}
            onSend={assistant.send}
            placeholder="שאל שאלה כללית…"
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function NoteBanner({ color, bg, border, text }: { color: string; bg: string; border: string; text: string }) {
  return (
    <div
      className="flex items-center gap-[9px] text-[12px] font-semibold rounded-[10px] mb-3.5"
      style={{ padding: '10px 14px', color, background: bg, border: `1px solid ${border}` }}
    >
      <Info size={15} />
      <span>{text}</span>
    </div>
  )
}
