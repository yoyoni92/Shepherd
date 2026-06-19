'use client'
import { useState } from 'react'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function Shell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  return (
    <div className="flex min-h-screen">
      <Sidebar collapsed={collapsed} />
      <main className="flex-1 min-w-0 flex flex-col h-screen overflow-hidden">
        <Topbar onToggle={() => setCollapsed((c) => !c)} />
        <div className="flex-1 overflow-y-auto" style={{ padding: '24px 26px 40px' }}>
          {children}
        </div>
      </main>
    </div>
  )
}
