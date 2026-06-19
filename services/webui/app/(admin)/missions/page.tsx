'use client'
import { Plus, User, Truck, Clock } from 'lucide-react'
import { useMissions } from '@/hooks/useMissions'
import { Button } from '@/components/ui/button'
import { PreviewBanner } from '@/components/PreviewBanner'
import { PRIORITY_META, MISSION_STATUS_META } from '@/components/meta'

export default function MissionsPage() {
  const { missions } = useMissions()

  return (
    <div className="animate-fade-up" style={{ maxWidth: 980 }}>
      <PreviewBanner>נתוני דמו — אין עדיין API למשימות (API_ALIGNMENT.md · B1)</PreviewBanner>
      <div className="flex items-center gap-2.5 mb-4">
        <span className="text-[13px] text-faint font-semibold">ממוין לפי עדיפות · גבוהה ← נמוכה</span>
        <div className="flex-1" />
        <Button>
          <Plus size={16} strokeWidth={2.4} />
          משימה חדשה
        </Button>
      </div>

      <div className="flex flex-col gap-[11px]">
        {missions.map((m) => {
          const prio = PRIORITY_META[m.priority]
          const st = MISSION_STATUS_META[m.status]
          return (
            <div
              key={m.id}
              className="flex items-stretch bg-panel border border-line rounded-[13px] overflow-hidden"
            >
              <div style={{ width: 5, minWidth: 5, background: prio.color }} />
              <div className="flex-1 flex items-center gap-4 min-w-0" style={{ padding: '15px 18px' }}>
                <div
                  className="text-[12px] font-extrabold rounded-lg text-center whitespace-nowrap"
                  style={{ color: prio.color, background: prio.bg, padding: '7px 13px', minWidth: 64 }}
                >
                  {prio.label}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[15px] font-bold mb-1">{m.title}</div>
                  <div className="flex items-center gap-3.5 flex-wrap text-[12px] text-faint">
                    <span className="flex items-center gap-[5px]">
                      <User size={13} />
                      {m.driver}
                    </span>
                    <span className="flex items-center gap-[5px] ltr">
                      <Truck size={13} />
                      {m.vehicle}
                    </span>
                    <span className="flex items-center gap-[5px]">
                      <Clock size={13} />
                      {m.due}
                    </span>
                  </div>
                </div>
                <span
                  className="text-[11.5px] font-bold rounded-md whitespace-nowrap"
                  style={{ color: st.color, background: st.bg, padding: '5px 11px' }}
                >
                  {st.label}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
