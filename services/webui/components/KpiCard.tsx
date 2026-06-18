const colorMap = {
  blue: 'text-blue-300',
  green: 'text-emerald-300',
  amber: 'text-amber-300',
  rose: 'text-rose-300',
  purple: 'text-violet-300',
  orange: 'text-orange-300',
}

interface KpiCardProps {
  value: number | string
  label: string
  color: keyof typeof colorMap
}

export function KpiCard({ value, label, color }: KpiCardProps) {
  return (
    <div className="bg-panel border border-line rounded-xl p-3.5">
      <div className={`text-2xl font-extrabold ${colorMap[color]}`}>{value}</div>
      <div className="text-[10.5px] text-muted uppercase tracking-wider mt-0.5">{label}</div>
    </div>
  )
}
