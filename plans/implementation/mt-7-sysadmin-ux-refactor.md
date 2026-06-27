# Impl: Feature 7 - System-admin UX refactor + attendance config relocation

**Status**: in-progress
**Mode**: ponytail + TDD + frontend-design (within the existing dark/RTL design system)
**Depends on**: Features 1-6

## Goal

Declutter the system-admin console, redesign the Companies (חברות) per-company
settings (currently poor UX), and relocate attendance window config from
הגדרות (system-admin) to נוכחות (company-admin) as a Configuration tab, gated by
the system-admin per-company attendance enable.

## Decisions (grilled)

- **Nav**: remove נוכחות from the **system-admin** sidebar (operators don't run
  attendance); company admins keep it (flag-gated).
- **Companies redesign**: attendance **enable** becomes a clean per-company row
  toggle (writes `feature_flags.attendance` via the existing
  `/companies/{id}/settings`); the settings **dialog** is rebuilt as a polished,
  Drive-focused form (folder + write-only credentials + inline validation).
- **Attendance config relocation**: delete the `AttendanceWindowCard` from
  הגדרות; the company-admin Attendance page gains **Records | Configuration**
  tabs; Configuration holds the window (enabled + start/end), shown when the
  company has attendance enabled.
- **Backend (least privilege)**: a narrow company-scoped `GET/PUT
  /attendance/settings` for the window keys, gated by `MANAGE_ATTENDANCE` (which
  company_admin already holds), scoped to `caller.company_id`. Does NOT open
  general `EDIT_CONFIG` to company admins.

## Slices

Backend (TDD) - DOING NOW:
- [x] **E1** `GET/PUT /attendance/settings` (window keys, MANAGE_ATTENDANCE, scoped to
      caller.company_id; 400 if no company). test_attendance_settings.py; fleet-api 160 passed.

Webui (frontend-design) - AFTER:
- [x] **E2** nav: remove נוכחות for role=admin (keep company_admin flag-gated). filterNav now
      hides flag-gated items from role=admin; nav.test.ts updated.
- [x] **E3** Companies page redesign: row attendance toggle (role="switch", writes
      feature_flags.attendance via /companies/{id}/settings); rebuilt Drive-focused settings
      dialog (sectioned card, folder-id + write-only creds with helper text, "מוגדר ✓" chip,
      inline 400/success feedback, save loading). Attendance toggle removed from the dialog.
- [x] **E4** הגדרות: removed the AttendanceWindowCard (config page now numeric fields only).
- [x] **E5** נוכחות: נוכחות | הגדרות tabs (shadcn Tabs); הגדרות = clock-in window via the new
      endpoint. Added fetch/updateAttendanceSettings (fleet.ts), AttendanceSettingsSchema
      (schemas.ts), useAttendanceSettings hook (+ test). MSW handlers for /attendance/settings.

- [x] **E6** Vehicles RTL fix: Radix `Tabs.Root` rendered `<div dir="ltr">` (useDirection
      defaults to ltr), forcing the tabbed content LTR - the sort chips flowed LTR and the
      add-car button landed on the wrong side. Defaulted `components/ui/tabs.tsx` Tabs root to
      `dir="rtl"`; fixes Vehicles + Events headers in one place.

## Verify

`cd services/fleet-api && poetry run pytest -q` ; `cd services/webui && npm test` (+ build/typecheck/lint) ; Playwright e2e.

## Running log / decisions

- 2026-06-28: grilled (grill-me). System admin keeps a minimal attendance enable (row
  toggle); attendance window config moves הגדרות -> נוכחות (company admin), via a narrow
  MANAGE_ATTENDANCE-gated endpoint. UI via frontend-design within the existing theme.
- 2026-06-28: E2-E5 webui done (ponytail + TDD). filterNav hides flag-gated nav from
  role=admin; Companies page got a per-row attendance switch + Drive-focused settings
  dialog; AttendanceWindowCard removed from הגדרות; Attendance page wrapped in
  נוכחות|הגדרות tabs backed by GET/PUT /attendance/settings via useAttendanceSettings.
  webui: 115 tests pass; typecheck/lint/build clean. No fleet-api/bot changes.
