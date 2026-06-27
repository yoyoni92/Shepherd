'use client'
import { AccidentsPanel } from '@/components/AccidentsPanel'

// Nav consolidation (Feature 4): this lives as a tab inside Events; the route
// stays reachable but is no longer a top-level sidebar item.
export default function AccidentsPage() {
  return <AccidentsPanel />
}
