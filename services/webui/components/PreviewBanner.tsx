import { TriangleAlert } from 'lucide-react'

/** Marks a section that runs on sample data because its backend does not exist yet. */
export function PreviewBanner({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="flex items-center gap-[9px] text-[12px] font-semibold rounded-[10px] mb-4"
      style={{ padding: '10px 14px', color: '#fbbf24', background: 'rgba(251,191,36,.07)', border: '1px solid #4a3a1a' }}
    >
      <TriangleAlert size={15} />
      <span>{children}</span>
    </div>
  )
}
