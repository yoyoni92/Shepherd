# Accidents Page - Design Spec

Date: 2026-06-21

## Overview

A new top-level admin page at `/accidents` that lists all logged accidents as
cards (Option A - matching the vehicles/drivers/customers pattern) and lets
admins create new accidents via a dedicated form modal with optional file
uploads.

## Architecture

Three layers change:

1. **fleet-api** - two new endpoints (list accidents, upload accident file)
2. **webui lib** - new types and hook
3. **webui UI** - new page, card component, form modal, sidebar entry

## API changes (fleet-api)

### GET /accidents

Returns all accidents ordered by `datetime` desc. Each item includes its
`accident_attachments` array.

Response shape (per item):
```json
{
  "accident_id": "uuid",
  "vehicle_id": "uuid",
  "driver_id": "uuid | null",
  "datetime": "ISO-8601",
  "location": "string | null",
  "description": "string | null",
  "another_driver_licensing_plate": "string | null",
  "another_driver_phone_number": "string | null",
  "another_driver_id_number": "string | null",
  "attachments": [
    { "attachment_id": "uuid", "category": "photo_our_vehicle", "file_url": "s3://...", "uploaded_ts": "ISO-8601" }
  ]
}
```

Repo function: `list_accidents(session)` - queries `accidents` + eagerly loads
`accident_attachments` via SQLAlchemy relationship, ordered by `datetime desc`.

### POST /uploads/accident-file

Accepts `multipart/form-data` with a single `file` field. Uploads to
`S3_BUCKET_ACCIDENTS` (env var, default `shepherd-accidents`) using boto3
`put_object`, key pattern: `accidents/<uuid>/<original_filename>`. Returns
`{ "file_url": "s3://shepherd-accidents/<key>" }`. Admin-only.

Auth: same `assert_permitted` pattern as other write endpoints.

## WebUI types (lib/api/schemas.ts)

```ts
interface UiAccidentAttachment {
  id: string
  category: string
  fileUrl: string
  uploadedTs: string
}

interface UiAccident {
  id: string
  vehicleId: string
  vehiclePlate: string      // resolved from vehicles list
  vehicleMake: string       // resolved from vehicles list
  vehicleModel: string      // resolved from vehicles list
  driverId: string | null
  driverName: string | null // resolved from drivers list
  datetime: string
  location: string | null
  description: string | null
  anotherDriverPlate: string | null
  anotherDriverPhone: string | null
  anotherDriverIdNumber: string | null
  attachments: UiAccidentAttachment[]
}
```

Zod schemas follow the same pattern as `UiVehicle` etc.

## Hook (hooks/useAccidents.ts)

`useAccidents()` - fetches `GET /accidents` via fleet-api client, returns
`{ accidents: UiAccident[], add: (payload) => void }`.

Resolution of `vehiclePlate`/`vehicleMake`/`vehicleModel` and `driverName` is
done client-side against the existing `useVehicles()` and `useDrivers()` lists,
same pattern as `driverById` in the vehicles page.

`add()` - POSTs to `POST /accidents` (existing endpoint) with the constructed
payload including resolved S3 keys.

## AccidentCard component

Layout matches VehicleCard - `Card` wrapper, same spacing tokens.

**Header:** vehicle type icon + "{make} {model}" bold title + plate badge (same
blue LTR chip as VehicleCard) + formatted date.

**Body grid (2-col):**
- נהג משויך / תאריך ושעה
- מיקום / תיאור
- לוחית רכב שני / טלפון נהג שני
- ת.ז. נהג שני / (empty or future field)

**Attachments section** (shown only when `attachments.length > 0`):

Each attachment is a small chip: category icon + Hebrew label + external-link
icon. Clicking opens `file_url` in a new tab. Categories with icons:

| Category | Hebrew | Icon |
|----------|--------|------|
| photo_our_vehicle | צילום רכבנו | `Image` |
| photo_other_vehicle | צילום רכב שני | `Image` |
| photo_accident_area | צילום מקום | `Image` |
| another_driver_insurance | ביטוח נהג שני | `FileText` |
| another_car_registration | רישום רכב שני | `FileText` |
| another_driver_license | רישיון נהג שני | `FileText` |
| accident_video | וידאו תאונה | `Film` |

## AccidentFormModal component

Dedicated modal (not reusing `EntityFormModal` - file inputs are not
supported there).

**Required fields:**
- `vehicle_id` - select from vehicles list; option labels show "{plate} - {make} {model}"
- `datetime` - `<input type="datetime-local">`

**Optional select fields:**
- `driver_id` - select from drivers list; option labels show driver name

**Optional text fields:**
- `location` - text
- `description` - text
- `another_driver_licensing_plate` - text, LTR
- `another_driver_phone_number` - text
- `another_driver_id_number` - text

fleet-api `AccidentCreate` schema must accept an optional `driver_id` field so
admin callers can assign the driver. The router currently ignores `driver_id`
from the request body for admin callers - that logic must be updated to use the
supplied value when present.

**Optional file slots** (one per category, all optional):

Each slot is a small drop-zone (drag-and-drop or click-to-pick). Accepted
types: `image/*,application/pdf,video/*`. States: idle / uploading / done
(shows filename) / error. On submit, only slots with a completed upload are
included as attachments. Upload happens on file selection (not on submit), so
the user sees per-file status before submitting.

File slot order matches the Hebrew table above.

**Submit flow:**
1. Validate required fields.
2. Any file not yet uploaded at submit time is skipped (already uploading slots
   wait for completion).
3. POST `/accidents` with all text fields + collected `attachments[]`.
4. On success: close modal, refresh accidents list.

## Accidents page (app/(admin)/accidents/page.tsx)

- `animate-fade-up` wrapper, same as other pages.
- Top bar: title or sort chips (TBD - start without sort, add if requested).
- "הוסף תאונה" button top-right, opens `AccidentFormModal`.
- Card grid: `repeat(auto-fill, minmax(330px, 1fr))`, same as vehicles page.

## Sidebar

New entry after "משימות" (events), before "נוכחות" (attendance):

```ts
{ href: '/accidents', label: 'תאונות', Icon: ShieldAlert, badge: 'accidents' }
```

Badge shows total accident count. `counts.accidents = accidents.length` added
to the Sidebar hook map.

## Out of scope

- Edit/delete accidents (write-once log, can be added later).
- Filtering/sorting accidents (add when fleet grows large enough to need it).
- Presigned URL direct-to-S3 upload (fleet-api proxy upload is simpler and
  consistent with existing boto3 usage).
