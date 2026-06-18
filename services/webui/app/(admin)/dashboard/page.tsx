'use client'
import { useKpis } from '@/hooks/useKpis'
import { KpiCard } from '@/components/KpiCard'

export default function DashboardPage() {
  const { data: kpis } = useKpis()
  return (
    <div>
      <h2 className="text-[15px] font-bold mb-4">Dashboard</h2>
      <div className="grid grid-cols-6 gap-3 mb-5">
        <KpiCard value={kpis?.vehicles ?? '-'} label="Vehicles" color="blue" />
        <KpiCard value={kpis?.activeDrivers ?? '-'} label="Active drivers" color="green" />
        <KpiCard value={kpis?.docsExpiring30d ?? '-'} label="Docs expiring 30d" color="amber" />
        <KpiCard value={kpis?.openEvents ?? '-'} label="Open events" color="purple" />
        <KpiCard value={kpis?.unpaidTickets ?? '-'} label="Unpaid tickets" color="rose" />
        <KpiCard value={kpis?.maintenanceDue ?? '-'} label="Maintenance due" color="orange" />
      </div>
    </div>
  )
}
