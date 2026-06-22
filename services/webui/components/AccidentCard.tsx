'use client'
import { ExternalLink, FileText, Film, Image as ImageIcon, type LucideIcon } from 'lucide-react'
import type { UiAccident } from '@/lib/api/schemas'
import { fmtDateTime } from '@/lib/domain'
import { Card } from '@/components/ui/card'

const DASH = '-'

const ATTACHMENT_LABEL: Record<string, string> = {
  photo_our_vehicle: 'צילום רכבנו',
  photo_other_vehicle: 'צילום רכב שני',
  photo_accident_area: 'צילום מקום',
  another_driver_insurance: 'ביטוח נהג שני',
  another_car_registration: 'רישום רכב שני',
  another_driver_license: 'רישיון נהג שני',
  accident_video: 'וידאו תאונה',
}

const ATTACHMENT_ICON: Record<string, LucideIcon> = {
  photo_our_vehicle: ImageIcon,
  photo_other_vehicle: ImageIcon,
  photo_accident_area: ImageIcon,
  another_driver_insurance: FileText,
  another_car_registration: FileText,
  another_driver_license: FileText,
  accident_video: Film,
}

function Field({ label, value, ltr }: { label: string; value: string; ltr?: boolean }) {
  return (
    <div>
      <div className="text-[11px] text-faint mb-0.5">{label}</div>
      <div className={`text-[13px] font-semibold${ltr ? ' ltr' : ''}`}>{value}</div>
    </div>
  )
}

export function AccidentCard({ a }: { a: UiAccident }) {
  return (
    <Card style={{ padding: '17px 18px' }}>
      <div className="flex items-start gap-3 mb-3.5 min-w-0">
        <div className="min-w-0">
          <div className="text-[15.5px] font-bold truncate">
            {a.vehicleMake} {a.vehicleModel}
          </div>
          <div className="text-[12px] text-faint ltr">{fmtDateTime(a.datetime)}</div>
        </div>
      </div>

      <div
        className="inline-flex items-center gap-[7px] bg-bg border border-control rounded-lg mb-3.5 ltr"
        style={{ padding: '6px 11px' }}
      >
        <span className="rounded-sm" style={{ width: 13, height: 9, background: '#2563eb' }} />
        <span className="text-[14px] font-bold font-mono" style={{ letterSpacing: 2 }}>
          {a.vehiclePlate}
        </span>
      </div>

      <div className="grid grid-cols-2 mb-3.5" style={{ gap: '11px 14px' }}>
        <Field label="נהג משויך" value={a.driverName ?? DASH} />
        <Field label="מיקום" value={a.location ?? DASH} />
        <Field label="תיאור" value={a.description ?? DASH} />
        <Field label="לוחית רכב שני" value={a.anotherDriverPlate ?? DASH} ltr />
        <Field label="טלפון נהג שני" value={a.anotherDriverPhone ?? DASH} ltr />
        <Field label="ת.ז. נהג שני" value={a.anotherDriverIdNumber ?? DASH} />
      </div>

      {a.attachments.length > 0 && (
        <div className="border-t border-line pt-3 flex flex-wrap gap-2">
          {a.attachments.map((att) => {
            const Icon = ATTACHMENT_ICON[att.category] ?? FileText
            return (
              <a
                key={att.id}
                href={att.fileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-[12px] font-semibold border border-control rounded-lg bg-panel2 hover:bg-panel"
                style={{ padding: '5px 10px' }}
              >
                <Icon size={13} />
                {ATTACHMENT_LABEL[att.category] ?? att.category}
                <ExternalLink size={11} className="text-faint" />
              </a>
            )
          })}
        </div>
      )}
    </Card>
  )
}
