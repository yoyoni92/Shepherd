'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { signOut, useSession } from 'next-auth/react'

const NAV = [
  { href: '/dashboard', icon: '▦', label: 'Dashboard' },
  { href: '/chat', icon: '◆', label: 'Fleet Chat' },
  { href: '/assistant', icon: '✦', label: 'Assistant' },
  { href: '/upload', icon: '⬆', label: 'Upload' },
  { href: '/config', icon: '⚙', label: 'Config' },
  { href: '/review', icon: '⚑', label: 'Review Queue' },
]

export function Sidebar() {
  const pathname = usePathname()
  const { data: session } = useSession()
  const initials = session?.user?.name?.[0]?.toUpperCase() ?? 'A'

  return (
    <aside className="bg-panel2 border-r border-line flex flex-col p-4" style={{ width: 212 }}>
      <div className="flex items-center gap-2.5 mb-5">
        <img src="/logo.png" alt="Shepherd" className="w-8 h-8" style={{ mixBlendMode: 'lighten' }} />
        <span className="font-extrabold text-sm tracking-tight">Shepherd</span>
      </div>
      <nav className="flex flex-col gap-1 flex-1">
        {NAV.map(({ href, icon, label }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[12.5px] font-semibold transition-colors ${
              pathname?.startsWith(href)
                ? 'bg-blue-950 text-blue-200 border border-blue-900'
                : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
            }`}
          >
            <span className="w-4 text-center opacity-90 text-sm">{icon}</span>
            {label}
          </Link>
        ))}
      </nav>
      <div className="border-t border-line pt-3 mt-2 flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-indigo-950 border border-purple-800 text-violet-300 flex items-center justify-center font-bold text-xs">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold truncate">{session?.user?.name ?? 'Admin'}</div>
          <div className="text-[10px] text-muted">Administrator</div>
        </div>
        <button
          onClick={() => signOut({ callbackUrl: '/' })}
          className="text-muted hover:text-rose-400 text-xs bg-transparent border-none cursor-pointer"
        >
          Logout
        </button>
      </div>
    </aside>
  )
}
