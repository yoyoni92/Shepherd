'use client'
import { useState } from 'react'
import { useEvents } from '@/hooks/useEvents'
import { sortEvents } from '@/lib/events'
import { EventRow } from '@/components/EventRow'
import { EVENT_TYPE_LABEL, SEVERITY_META, EVENT_STATUS_META } from '@/components/meta'

const ANY = ''

function Select({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
  placeholder: string
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-bg border border-control rounded-[9px] text-[13px] text-ink outline-none focus:border-accent"
      style={{ padding: '8px 10px' }}
    >
      <option value={ANY}>{placeholder}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  )
}

const metaOptions = (m: Record<string, { label: string }>) =>
  Object.entries(m).map(([value, { label }]) => ({ value, label }))

const labelOptions = (m: Record<string, string>) =>
  Object.entries(m).map(([value, label]) => ({ value, label }))

export default function EventsPage() {
  const { events } = useEvents()
  const [type, setType] = useState(ANY)
  const [severity, setSeverity] = useState(ANY)
  const [status, setStatus] = useState(ANY)
  const [vehicle, setVehicle] = useState(ANY)

  const vehicleIds = [...new Set(events.map((e) => e.vehicle_id).filter(Boolean) as string[])]

  const filtered = sortEvents(
    events.filter(
      (e) =>
        (!type || e.event_type === type) &&
        (!severity || e.severity === severity) &&
        (!status || e.status === status) &&
        (!vehicle || e.vehicle_id === vehicle),
    ),
  )

  return (
    <div className="animate-fade-up" style={{ maxWidth: 980 }}>
      <div className="flex items-center gap-2.5 mb-4 flex-wrap">
        <Select value={type} onChange={setType} placeholder="כל הסוגים" options={labelOptions(EVENT_TYPE_LABEL)} />
        <Select value={severity} onChange={setSeverity} placeholder="כל החומרות" options={metaOptions(SEVERITY_META)} />
        <Select value={status} onChange={setStatus} placeholder="כל הסטטוסים" options={metaOptions(EVENT_STATUS_META)} />
        <Select
          value={vehicle}
          onChange={setVehicle}
          placeholder="כל הרכבים"
          options={vehicleIds.map((id) => ({ value: id, label: id }))}
        />
        <div className="flex-1" />
        <span className="text-[13px] text-faint font-semibold">{filtered.length} אירועים</span>
      </div>

      <div className="flex flex-col gap-[11px]">
        {filtered.length === 0 && <div className="text-[13px] text-faint">אין אירועים תואמים</div>}
        {filtered.map((e) => (
          <EventRow key={e.event_id} e={e} />
        ))}
      </div>
    </div>
  )
}
