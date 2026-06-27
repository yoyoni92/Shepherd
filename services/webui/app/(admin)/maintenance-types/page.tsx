'use client'
import { MaintenanceTypesPanel } from '@/components/MaintenanceTypesPanel'

// Nav consolidation (Feature 4): this lives as a tab inside Vehicles; the route
// stays reachable but is no longer a top-level sidebar item.
export default function MaintenanceTypesPage() {
  return <MaintenanceTypesPanel />
}
