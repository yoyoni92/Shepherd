'use client'
import { usePathname } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { Menu, Search, Bell } from 'lucide-react'
import { useVehicles } from '@/hooks/useVehicles'
import { useDrivers } from '@/hooks/useDrivers'
import { initials } from '@/lib/domain'

function useTitle(): [string, string] {
  const pathname = usePathname() ?? ''
  const { vehicles } = useVehicles()
  const { drivers } = useDrivers()
  const seg = pathname.split('/')[1] || 'dashboard'
  const map: Record<string, [string, string]> = {
    dashboard: ['לוח בקרה', 'סקירת מצב הצי בזמן אמת'],
    vehicles: ['רכבים', `${vehicles.length} רכבים בצי · ניהול וסינון`],
    drivers: ['נהגים', `${drivers.length} נהגים רשומים`],
    events: ['אירועים', 'התראות תפעוליות לפי חומרה'],
    attendance: ['נוכחות עובדים', 'דוח כניסה/יציאה חודשי'],
    config: ['הגדרות מערכת', 'עריכת ספי system_config'],
    chat: ['צ׳אט ועוזר חכם', 'שתי מערכות שיחה נפרדות'],
    assistant: ['עוזר כללי', 'עוזר Ollama ללא גישה לנתונים'],
    upload: ['העלאת מסמכים', 'ערוץ קליטה דרך הקונסולה'],
  }
  return map[seg] ?? ['ניהול צי רכב', '']
}

export function Topbar({ onToggle }: { onToggle: () => void }) {
  const [title, sub] = useTitle()
  const { data: session } = useSession()
  const name = session?.user?.name ?? 'אבי כהן'

  return (
    <header
      className="border-b border-line flex items-center gap-4 bg-raised shrink-0"
      style={{ height: 64, minHeight: 64, padding: '0 26px' }}
    >
      <button
        onClick={onToggle}
        aria-label="כווץ תפריט"
        className="bg-panel2 border border-control rounded-lg w-9 h-9 flex items-center justify-center text-muted cursor-pointer hover:text-ink"
      >
        <Menu size={17} />
      </button>
      <div>
        <div className="text-[17px] font-extrabold" style={{ letterSpacing: '-.2px' }}>
          {title}
        </div>
        <div className="text-[11.5px] text-faint">{sub}</div>
      </div>
      <div className="flex-1" />
      <div className="relative flex items-center">
        <Search size={15} className="absolute right-[11px] text-dim" />
        <input
          placeholder="חיפוש רכב, נהג, משימה…"
          className="bg-bg border border-control rounded-[9px] text-[13px] text-ink outline-none focus:border-accent"
          style={{ width: 230, padding: '9px 34px 9px 12px' }}
        />
      </div>
      <button
        aria-label="התראות"
        className="relative bg-panel2 border border-control rounded-lg w-9 h-9 flex items-center justify-center text-muted cursor-pointer hover:text-ink"
      >
        <Bell size={17} />
        <span
          className="absolute bg-danger text-white text-[9px] font-bold rounded-lg flex items-center justify-center"
          style={{ top: -3, left: -3, minWidth: 15, height: 15, padding: '0 3px' }}
        >
          5
        </span>
      </button>
      <div className="flex items-center gap-2.5 pr-1.5 border-r border-line mr-0.5">
        <div
          className="flex items-center justify-center font-bold text-[13px] text-white"
          style={{
            width: 34,
            height: 34,
            borderRadius: 9,
            background: 'linear-gradient(135deg,#6366f1,#4338ca)',
          }}
        >
          {initials(name)}
        </div>
        <div className="leading-[1.25]">
          <div className="text-[13px] font-bold">{name}</div>
          <div className="text-[11px] text-faint">מנהל מערכת</div>
        </div>
      </div>
    </header>
  )
}
