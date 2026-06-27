'use client'
import { useState } from 'react'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { ActAsBanner } from './ActAsBanner'
import type { ActAsState } from '@/lib/actAs'

export function Shell({ actAs, children }: { actAs: ActAsState | null; children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  return (
    <div className="flex min-h-screen">
      <Sidebar collapsed={collapsed} actAs={actAs} />
      <main className="flex-1 min-w-0 flex flex-col h-screen overflow-hidden">
        {actAs && <ActAsBanner actAs={actAs} />}
        <Topbar onToggle={() => setCollapsed((c) => !c)} actAs={actAs} />
        <div className="flex-1 overflow-y-auto" style={{ padding: '24px 26px 40px' }}>
          {children}
        </div>
      </main>
    </div>
  )
}
