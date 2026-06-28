# Impl: Attendance - Jewish-holiday notes + configurable working days

Extends the company-scoped Attendance settings (see `mt-7-sysadmin-ux-refactor.md`,
which owns the `GET/PUT /attendance/settings` contract) with working-day rules, and
overlays Jewish-holiday notes onto the monthly attendance report.

## Decisions

- **Holiday source**: `@hebcal/core` (npm) in the webui - perpetual (computes any year
  offline), Israeli schedule via `il: true`. Chosen over the Hebcal REST API per Hebcal's
  own guidance for JS apps (no rate limits, no network failure mode). Holidays are computed
  entirely client-side; no backend holiday logic or endpoint.
- **Holiday classification** (`lib/holidays.ts`): event flags map to
  `chag` (Yom Tov, melacha forbidden) | `erev` (holiday eve) | `fast` | `minor`
  (Chol HaMoed, modern/festive days). Per Gregorian day the most significant kind wins.
- **Working-day rules** are part of the admin Attendance Configuration tab:
  - `work_days`: weekday numbers (0=Sun..6=Sat) that are regular work days. שבת is just the
    Saturday checkbox. Default `[0,1,2,3,4]` (Sun-Thu).
  - `chag_working`: are חג days work days? Default `false`.
  - `erev_chag_working`: are ערב חג days work days? Default `true`.
  - A calendar day is in the skeleton iff `weekday ∈ work_days` AND (chag -> chag_working)
    AND (erev -> erev_chag_working). Non-working days are skipped, so holidays/weekends are
    never counted as `absent`. Minor/fast days stay work days and carry only a note.
- **Notes visibility**: WebUI נוכחות grid (a "חגי ומועדי החודש" banner, which also covers
  PDF since export is `window.print()`), the per-day edit modal (note under each date), and
  the CSV export (appended "חגים ומועדים" section). Telegram bot is untouched.

## Contract change

`AttendanceSettings` (fleet-api `schemas.py` + webui `lib/api/schemas.ts`) gains:
`work_days: number[]`, `chag_working: bool`, `erev_chag_working: bool`. Persisted as
`system_config` keys `attendance_work_days` / `attendance_chag_working` /
`attendance_erev_chag_working`, company-scoped, defaults applied on read. No DB migration
(JSONB key-value; schema is rebuilt from models in dev).

## Files

- `services/webui/lib/holidays.ts` (new) - `monthHolidays`, `holidayMap`, `Holiday`.
- `services/webui/lib/attendance.ts` - `note` on `AttendanceDay`; `WorkDayConfig`;
  `buildMonthSkeleton(monthKey, employees, config?)`; `buildCsv(..., holidays?)`.
- `services/webui/hooks/useAttendance.ts` - reads settings + holidays, returns `holidays`.
- `services/webui/components/meta.ts` - `HOLIDAY_META` pills.
- `services/webui/app/(admin)/attendance/page.tsx` - holidays banner + config UI
  (weekday picker, חג / ערב חג toggles).
- `services/webui/components/AttendanceEditModal.tsx` - per-day note line.
- `services/fleet-api/app/routers/attendance.py` - `_work_rules`; settings read/write.
- `services/fleet-api/app/schemas.py` - extended `AttendanceSettings`.

## Tests

- [x] webui `tests/holidays.test.ts` - Pesach 2026 classification (erev/chag/minor, il).
- [x] webui `tests/attendance.test.ts` - skeleton work-day rules (workDays, chag/erev,
      note overlay) + CSV holidays section.
- [x] webui `tests/useAttendanceSettings.test.tsx` + MSW handlers - new fields round-trip.
- [x] fleet-api `tests/test_attendance_settings.py` - working-day rules round-trip.

## Definition of Done

- [x] webui: `tsc --noEmit`, ESLint, and Vitest (139) all green.
- [x] fleet-api: attendance + settings pytest green.
