# Accidents Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a top-level `/accidents` page to the admin UI where accidents are displayed as cards (with full details + S3 attachment links) and new accidents can be created via a form modal with optional file uploads.

**Architecture:** Three layers change: (1) fleet-api gets `GET /accidents` + updated `POST /accidents` (admin can supply `driver_id`); (2) webui adds a Next.js upload route to S3, type definitions, a fleet client function, and an adapter; (3) webui adds `useAccidents` hook, `AccidentCard`, `AccidentFormModal`, the `/accidents` page, and a Sidebar entry.

**Tech Stack:** FastAPI + SQLAlchemy (fleet-api), Next.js 14 App Router + React + TanStack Query + Zod + `@aws-sdk/client-s3` (webui)

## Global Constraints

- All Hebrew copy uses the exact strings in the spec (e.g. `'תאונות'`, `'הוסף תאונה'`, `'צילום רכבנו'`, etc.)
- Spacing tokens match VehicleCard: `padding: '17px 18px'`, grid gap `'11px 14px'`, card grid `minmax(330px,1fr)`
- No edit/delete on accidents (write-once log)
- Fleet proxy (`/api/fleet/[...path]`) is unchanged - upload goes to its own `/api/accident-upload` route
- `S3_BUCKET_ACCIDENTS` env var, default `'shepherd-accidents'`
- Attachment `file_url` values are stored as-is (`s3://bucket/key`) and linked directly as `href` - no presigned URL generation
- Auth pattern: `assert_permitted(caller.role, Action.READ_ACCIDENTS)` for GET; admin-only
- `_to_read()` helper pattern (explicit field mapping, no ORM mode) - matches vehicles router

---

## File Map

**fleet-api - modified:**
- `db/shepherd_db/models.py` - add `attachments` relationship to `Accident`
- `services/fleet-api/app/auth.py` - add `READ_ACCIDENTS` action
- `services/fleet-api/app/schemas.py` - add `AccidentAttachmentOut`, `AccidentListItem`; add `driver_id` to `AccidentCreate`
- `services/fleet-api/app/repo.py` - add `list_accidents()`
- `services/fleet-api/app/routers/accidents.py` - add `GET /accidents`; update `log_accident` to use `body.driver_id` for admin
- `services/fleet-api/tests/test_accidents.py` - add new test cases

**webui - modified:**
- `services/webui/lib/api/schemas.ts` - add `AccidentAttachmentReadSchema`, `AccidentReadSchema`, `AccidentCreateSchema`, `UiAccidentAttachment`, `UiAccident`, `AccidentCreate`
- `services/webui/lib/api/fleet.ts` - add `fetchAccidents()`, `createAccident()`
- `services/webui/lib/adapters.ts` - add `toUiAccident()`
- `services/webui/lib/domain.ts` - add `fmtDateTime()`
- `services/webui/components/Sidebar.tsx` - add `ShieldAlert` nav item + accidents badge

**webui - created:**
- `services/webui/app/api/accident-upload/route.ts` - Next.js API route: receive file, upload to S3, return `{ file_url }`
- `services/webui/hooks/useAccidents.ts`
- `services/webui/components/AccidentCard.tsx`
- `services/webui/components/AccidentFormModal.tsx`
- `services/webui/app/(admin)/accidents/page.tsx`

---

### Task 1: fleet-api - list accidents + driver_id on create

**Files:**
- Modify: `db/shepherd_db/models.py`
- Modify: `services/fleet-api/app/auth.py`
- Modify: `services/fleet-api/app/schemas.py`
- Modify: `services/fleet-api/app/repo.py`
- Modify: `services/fleet-api/app/routers/accidents.py`
- Modify: `services/fleet-api/tests/test_accidents.py`

**Interfaces:**
- Produces: `GET /accidents` returning `list[AccidentListItem]`
- Produces: `POST /accidents` now accepts optional `driver_id` field from admin callers

- [ ] **Step 1: Write failing tests**

Add to `services/fleet-api/tests/test_accidents.py`:

```python
def test_list_accidents_returns_list(client):
    r = client.get("/accidents", headers=admin_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_accidents_includes_attachments(client):
    vehicle_id = _make_vehicle(client)
    post = client.post(
        "/accidents",
        json={
            "vehicle_id": vehicle_id,
            "datetime": datetime.now(tz=timezone.utc).isoformat(),
            "location": "Haifa-list-test",
            "attachments": [
                {"category": "photo_our_vehicle", "file_url": "s3://bucket/photo.jpg"}
            ],
        },
        headers=admin_headers(),
    )
    assert post.status_code == 201

    r = client.get("/accidents", headers=admin_headers())
    items = r.json()
    match = next((i for i in items if i.get("location") == "Haifa-list-test"), None)
    assert match is not None
    assert len(match["attachments"]) == 1
    assert match["attachments"][0]["category"] == "photo_our_vehicle"
    assert match["attachments"][0]["file_url"] == "s3://bucket/photo.jpg"


def test_list_accidents_admin_sets_driver_id(client):
    driver_id = _make_driver(client)
    vehicle_id = _make_vehicle(client)
    post = client.post(
        "/accidents",
        json={
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "datetime": datetime.now(tz=timezone.utc).isoformat(),
        },
        headers=admin_headers(),
    )
    assert post.status_code == 201
    accident_id = post.json()["accident_id"]

    r = client.get("/accidents", headers=admin_headers())
    match = next((i for i in r.json() if str(i["accident_id"]) == accident_id), None)
    assert match is not None
    assert match["driver_id"] == driver_id


def test_list_accidents_forbidden_for_driver(client):
    driver_id = _make_driver(client)
    r = client.get("/accidents", headers=driver_headers(driver_id))
    assert r.status_code == 403
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd services/fleet-api && poetry run pytest tests/test_accidents.py -v -k "test_list"
```

Expected: 4 FAILED (404 or AttributeError - route does not exist yet)

- [ ] **Step 3: Add `attachments` relationship to `Accident` model**

In `db/shepherd_db/models.py`, update the `Accident` class (around line 358) and `AccidentAttachment` class (around line 384):

```python
class Accident(Base):
    __tablename__ = "accidents"

    accident_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=False,
    )
    driver_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id"),
        nullable=True,
    )
    datetime = mapped_column(DateTime(timezone=True), nullable=False)
    location = mapped_column(Text, nullable=True)
    description = mapped_column(Text, nullable=True)
    another_driver_licensing_plate = mapped_column(Text, nullable=True)
    another_driver_phone_number = mapped_column(Text, nullable=True)
    another_driver_id_number = mapped_column(Text, nullable=True)

    vehicle = relationship("Vehicle", foreign_keys=[vehicle_id])
    driver = relationship("Driver", foreign_keys=[driver_id])
    attachments = relationship("AccidentAttachment", back_populates="accident")  # NEW


class AccidentAttachment(Base):
    __tablename__ = "accident_attachments"

    attachment_id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    accident_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accidents.accident_id"),
        nullable=False,
    )
    category = mapped_column(accident_attachment_category_type, nullable=False)
    file_url = mapped_column(Text, nullable=False)
    uploaded_ts = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    accident = relationship("Accident", foreign_keys=[accident_id], back_populates="attachments")  # UPDATED
```

- [ ] **Step 4: Add `READ_ACCIDENTS` to auth.py**

In `services/fleet-api/app/auth.py`, add to `Action` enum:

```python
class Action(str, Enum):
    READ_VEHICLES = "read_vehicles"
    MANAGE_VEHICLES = "manage_vehicles"
    MANAGE_DRIVERS = "manage_drivers"
    MANAGE_CUSTOMERS = "manage_customers"
    KM_UPDATE = "km_update"
    LOG_ACCIDENT = "log_accident"
    READ_ACCIDENTS = "read_accidents"    # NEW
    LOG_CARE = "log_care"
    SUBMIT_DOCUMENT = "submit_document"
    WRITE_REPORTS = "write_reports"
    READ_REPORTS = "read_reports"
    READ_EVENTS = "read_events"
    WRITE_EVENTS = "write_events"
    READ_CONFIG = "read_config"
    EDIT_CONFIG = "edit_config"
    READ_KPI = "read_kpi"
    MANAGE_ATTENDANCE = "manage_attendance"
    MANAGE_MAINTENANCE_TYPES = "manage_maintenance_types"
    MANAGE_BOT_USERS = "manage_bot_users"
    MANAGE_BOT_INVITES = "manage_bot_invites"
```

And add to `_MATRIX` (after `Action.LOG_ACCIDENT` line):

```python
    Action.LOG_ACCIDENT:     {Role.admin: False, Role.driver: True,  Role.customer: None},
    Action.READ_ACCIDENTS:   {Role.admin: False, Role.driver: None,  Role.customer: None},  # NEW
```

- [ ] **Step 5: Add response schemas + update AccidentCreate in schemas.py**

In `services/fleet-api/app/schemas.py`, after the existing `AccidentRead` class (around line 155):

```python
class AccidentCreate(BaseModel):
    vehicle_id: UUID
    driver_id: UUID | None = None          # NEW - admin can specify driver
    datetime: datetime
    location: str | None = None
    description: str | None = None
    another_driver_licensing_plate: str | None = None
    another_driver_phone_number: str | None = None
    another_driver_id_number: str | None = None
    attachments: list[AccidentAttachmentIn] = []


class AccidentRead(BaseModel):
    accident_id: UUID


class AccidentAttachmentOut(BaseModel):
    attachment_id: UUID
    category: str
    file_url: str
    uploaded_ts: datetime


class AccidentListItem(BaseModel):
    accident_id: UUID
    vehicle_id: UUID
    driver_id: UUID | None
    datetime: datetime
    location: str | None
    description: str | None
    another_driver_licensing_plate: str | None
    another_driver_phone_number: str | None
    another_driver_id_number: str | None
    attachments: list[AccidentAttachmentOut]
```

- [ ] **Step 6: Add `list_accidents()` to repo.py**

In `services/fleet-api/app/repo.py`, add to the imports at the top:

```python
from sqlalchemy.orm import Session, selectinload
```

(Replace the existing `from sqlalchemy.orm import Session` line.)

Then add after the `create_accident` function (around line 229):

```python
def list_accidents(session: Session) -> list[Accident]:
    return list(session.scalars(
        select(Accident)
        .options(selectinload(Accident.attachments))
        .order_by(Accident.datetime.desc())
    ))
```

- [ ] **Step 7: Add GET /accidents route + update log_accident in accidents.py**

Replace `services/fleet-api/app/routers/accidents.py` entirely:

```python
from fastapi import APIRouter, HTTPException, status
from shepherd_contracts.auth import Role

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import (
    AccidentCreate,
    AccidentRead,
    AccidentListItem,
    AccidentAttachmentOut,
)

router = APIRouter(prefix="/accidents", tags=["accidents"])


def _to_list_item(a) -> AccidentListItem:
    return AccidentListItem(
        accident_id=a.accident_id,
        vehicle_id=a.vehicle_id,
        driver_id=a.driver_id,
        datetime=a.datetime,
        location=a.location,
        description=a.description,
        another_driver_licensing_plate=a.another_driver_licensing_plate,
        another_driver_phone_number=a.another_driver_phone_number,
        another_driver_id_number=a.another_driver_id_number,
        attachments=[
            AccidentAttachmentOut(
                attachment_id=att.attachment_id,
                category=att.category,
                file_url=att.file_url,
                uploaded_ts=att.uploaded_ts,
            )
            for att in a.attachments
        ],
    )


@router.get(
    "",
    response_model=list[AccidentListItem],
    summary="List all accidents",
    description="Returns all accidents ordered by datetime desc, with attachments. Admin only.",
)
def list_accidents(session: Db, caller: Caller) -> list[AccidentListItem]:
    assert_permitted(caller.role, Action.READ_ACCIDENTS)
    return [_to_list_item(a) for a in repo.list_accidents(session)]


@router.post(
    "",
    response_model=AccidentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log accident",
    description=(
        "Record an accident with optional attachments. "
        "Admin can log for any vehicle and supply driver_id; "
        "driver only for their own vehicle. "
        "Emits an accident_logged event."
    ),
)
def log_accident(body: AccidentCreate, session: Db, caller: Caller) -> AccidentRead:
    vehicle = repo.get_vehicle_by_id(session, body.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    if caller.role == Role.driver:
        is_owner = str(vehicle.driver_id) == caller.driver_id
    else:
        is_owner = True
    assert_permitted(caller.role, Action.LOG_ACCIDENT, is_owner=is_owner)

    if caller.role == Role.driver:
        driver_id = caller.driver_id
    else:
        driver_id = str(body.driver_id) if body.driver_id else None

    data = {
        "vehicle_id": body.vehicle_id,
        "driver_id": driver_id,
        "datetime": body.datetime,
        "location": body.location,
        "description": body.description,
        "another_driver_licensing_plate": body.another_driver_licensing_plate,
        "another_driver_phone_number": body.another_driver_phone_number,
        "another_driver_id_number": body.another_driver_id_number,
    }
    attachments = [a.model_dump() for a in body.attachments]
    accident_id = repo.create_accident(session, data, attachments)
    return AccidentRead(accident_id=accident_id)
```

- [ ] **Step 8: Run all accident tests**

```bash
cd services/fleet-api && poetry run pytest tests/test_accidents.py -v
```

Expected: all tests PASS (including the 4 new ones)

- [ ] **Step 9: Commit**

```bash
git add db/shepherd_db/models.py \
        services/fleet-api/app/auth.py \
        services/fleet-api/app/schemas.py \
        services/fleet-api/app/repo.py \
        services/fleet-api/app/routers/accidents.py \
        services/fleet-api/tests/test_accidents.py
git commit -m "add GET /accidents + driver_id on create, READ_ACCIDENTS action"
```

---

### Task 2: webui - types, fleet client, adapter

**Files:**
- Modify: `services/webui/lib/api/schemas.ts`
- Modify: `services/webui/lib/api/fleet.ts`
- Modify: `services/webui/lib/adapters.ts`

**Interfaces:**
- Produces: `AccidentRead`, `UiAccident`, `UiAccidentAttachment`, `AccidentCreate` exported from `schemas.ts`
- Produces: `fetchAccidents()`, `createAccident()` exported from `fleet.ts`
- Produces: `toUiAccident(a, vehicleById, driverById)` exported from `adapters.ts`

- [ ] **Step 1: Add schemas to schemas.ts**

At the bottom of `services/webui/lib/api/schemas.ts`, add:

```typescript
export const AccidentAttachmentReadSchema = z.object({
  attachment_id: z.string(),
  category: z.string(),
  file_url: z.string(),
  uploaded_ts: z.string(),
})

export const AccidentReadSchema = z.object({
  accident_id: z.string(),
  vehicle_id: z.string(),
  driver_id: z.string().nullish(),
  datetime: z.string(),
  location: z.string().nullish(),
  description: z.string().nullish(),
  another_driver_licensing_plate: z.string().nullish(),
  another_driver_phone_number: z.string().nullish(),
  another_driver_id_number: z.string().nullish(),
  attachments: z.array(AccidentAttachmentReadSchema),
})

export type AccidentRead = z.infer<typeof AccidentReadSchema>
export type AccidentAttachmentRead = z.infer<typeof AccidentAttachmentReadSchema>

export interface UiAccidentAttachment {
  id: string
  category: string
  fileUrl: string
  uploadedTs: string
}

export interface UiAccident {
  id: string
  vehicleId: string
  vehiclePlate: string
  vehicleMake: string
  vehicleModel: string
  driverId: string | null
  driverName: string | null
  datetime: string
  location: string | null
  description: string | null
  anotherDriverPlate: string | null
  anotherDriverPhone: string | null
  anotherDriverIdNumber: string | null
  attachments: UiAccidentAttachment[]
}

export interface AccidentCreate {
  vehicle_id: string
  driver_id?: string
  datetime: string
  location?: string
  description?: string
  another_driver_licensing_plate?: string
  another_driver_phone_number?: string
  another_driver_id_number?: string
  attachments: { category: string; file_url: string }[]
}
```

- [ ] **Step 2: Add fleet client functions to fleet.ts**

In `services/webui/lib/api/fleet.ts`, add these two lines to the existing `import { ... } from './schemas'` block (the one that already imports `VehicleReadSchema`, `DriverReadSchema`, etc.):

```typescript
  AccidentReadSchema,
  type AccidentCreate,
```

Then add at the bottom of the file:

```typescript
// Accidents
export const fetchAccidents = () => get('/accidents', z.array(AccidentReadSchema))
export const createAccident = (a: AccidentCreate): Promise<{ accident_id: string }> =>
  send('POST', '/accidents', a, z.object({ accident_id: z.string() }))
```

- [ ] **Step 3: Add `fmtDateTime` to domain.ts**

In `services/webui/lib/domain.ts`, add after the existing `fmtDate` function:

```typescript
/** ISO datetime -> DD/MM/YYYY HH:MM (local time, LTR-rendered). */
export function fmtDateTime(dateStr: string): string {
  const d = new Date(dateStr)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`
}
```

- [ ] **Step 4: Add `toUiAccident` adapter to adapters.ts**

In `services/webui/lib/adapters.ts`, add to the imports at the top:

```typescript
import type {
  VehicleRead,
  DriverRead,
  CustomerRead,
  MaintenanceTypeRead,
  AccidentRead,
  UiVehicle,
  UiDriver,
  UiCustomer,
  UiMaintenanceType,
  UiAccident,
  UiAccidentAttachment,
} from './api/schemas'
```

Then add at the bottom of the file:

```typescript
export function toUiAccident(
  a: AccidentRead,
  vehicleById: Record<string, UiVehicle>,
  driverById: Record<string, UiDriver>,
): UiAccident {
  const v = vehicleById[a.vehicle_id]
  const d = a.driver_id ? driverById[a.driver_id] : undefined
  return {
    id: a.accident_id,
    vehicleId: a.vehicle_id,
    vehiclePlate: v?.plate ?? '—',
    vehicleMake: v?.make ?? '—',
    vehicleModel: v?.model ?? '',
    driverId: a.driver_id ?? null,
    driverName: d?.name ?? null,
    datetime: a.datetime,
    location: a.location ?? null,
    description: a.description ?? null,
    anotherDriverPlate: a.another_driver_licensing_plate ?? null,
    anotherDriverPhone: a.another_driver_phone_number ?? null,
    anotherDriverIdNumber: a.another_driver_id_number ?? null,
    attachments: a.attachments.map((att) => ({
      id: att.attachment_id,
      category: att.category,
      fileUrl: att.file_url,
      uploadedTs: att.uploaded_ts,
    })),
  }
}
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd services/webui && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add services/webui/lib/api/schemas.ts \
        services/webui/lib/api/fleet.ts \
        services/webui/lib/adapters.ts \
        services/webui/lib/domain.ts
git commit -m "add UiAccident types, fetchAccidents client, toUiAccident adapter, fmtDateTime"
```

---

### Task 3: webui - S3 upload route + AccidentCard + AccidentFormModal

**Files:**
- Create: `services/webui/app/api/accident-upload/route.ts`
- Create: `services/webui/components/AccidentCard.tsx`
- Create: `services/webui/components/AccidentFormModal.tsx`

**Interfaces:**
- Produces: `POST /api/accident-upload` returns `{ file_url: string }`
- Produces: `<AccidentCard a={UiAccident} />` component
- Produces: `<AccidentFormModal vehicles={UiVehicle[]} drivers={UiDriver[]} onSubmit={fn} onClose={fn} submitting={bool} />`

- [ ] **Step 1: Install @aws-sdk/client-s3**

```bash
cd services/webui && npm install @aws-sdk/client-s3
```

Expected: package added to package.json and package-lock.json

- [ ] **Step 2: Create the upload API route**

Create `services/webui/app/api/accident-upload/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3'
import { randomUUID } from 'crypto'

const bucket = process.env.S3_BUCKET_ACCIDENTS ?? 'shepherd-accidents'
const s3 = new S3Client({ region: process.env.AWS_REGION ?? 'us-east-1' })

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const form = await req.formData()
  const file = form.get('file') as File | null
  if (!file) return NextResponse.json({ error: 'no file' }, { status: 400 })

  const key = `accidents/${randomUUID()}/${file.name}`
  const bytes = await file.arrayBuffer()

  await s3.send(new PutObjectCommand({
    Bucket: bucket,
    Key: key,
    Body: Buffer.from(bytes),
    ContentType: file.type || 'application/octet-stream',
  }))

  return NextResponse.json({ file_url: `s3://${bucket}/${key}` })
}
```

- [ ] **Step 3: Create AccidentCard component**

Create `services/webui/components/AccidentCard.tsx`:

```typescript
'use client'
import { ExternalLink, FileText, Film, Image as ImageIcon, type LucideIcon } from 'lucide-react'
import type { UiAccident } from '@/lib/api/schemas'
import { fmtDateTime } from '@/lib/domain'
import { Card } from '@/components/ui/card'

const DASH = '—'

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
```

- [ ] **Step 4: Create AccidentFormModal component**

Create `services/webui/components/AccidentFormModal.tsx`:

```typescript
'use client'
import { useState, useRef, useCallback } from 'react'
import { X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import type { UiVehicle, UiDriver, AccidentCreate } from '@/lib/api/schemas'
import { Button } from '@/components/ui/button'

type UploadState =
  | { status: 'idle' }
  | { status: 'uploading' }
  | { status: 'done'; fileUrl: string; fileName: string }
  | { status: 'error' }

const FILE_SLOTS = [
  { category: 'photo_our_vehicle',       label: 'צילום רכבנו',      accept: 'image/*' },
  { category: 'photo_other_vehicle',     label: 'צילום רכב שני',    accept: 'image/*' },
  { category: 'photo_accident_area',     label: 'צילום מקום',       accept: 'image/*' },
  { category: 'another_driver_insurance',label: 'ביטוח נהג שני',    accept: 'image/*,application/pdf' },
  { category: 'another_car_registration',label: 'רישום רכב שני',    accept: 'image/*,application/pdf' },
  { category: 'another_driver_license',  label: 'רישיון נהג שני',   accept: 'image/*,application/pdf' },
  { category: 'accident_video',          label: 'וידאו תאונה',      accept: 'video/*' },
] as const

const emptyUploads = (): Record<string, UploadState> =>
  Object.fromEntries(FILE_SLOTS.map((s) => [s.category, { status: 'idle' }]))

export function AccidentFormModal({
  vehicles,
  drivers,
  onSubmit,
  onClose,
  submitting,
}: {
  vehicles: UiVehicle[]
  drivers: UiDriver[]
  onSubmit: (payload: AccidentCreate) => void
  onClose: () => void
  submitting: boolean
}) {
  const [vehicleId, setVehicleId] = useState('')
  const [driverId, setDriverId] = useState('')
  const [datetime, setDatetime] = useState('')
  const [location, setLocation] = useState('')
  const [description, setDescription] = useState('')
  const [otherPlate, setOtherPlate] = useState('')
  const [otherPhone, setOtherPhone] = useState('')
  const [otherId, setOtherId] = useState('')
  const [uploads, setUploads] = useState<Record<string, UploadState>>(emptyUploads)
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const handleFile = useCallback(async (category: string, file: File) => {
    setUploads((u) => ({ ...u, [category]: { status: 'uploading' } }))
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/accident-upload', { method: 'POST', body: form })
      if (!res.ok) throw new Error('upload failed')
      const { file_url } = await res.json()
      setUploads((u) => ({ ...u, [category]: { status: 'done', fileUrl: file_url, fileName: file.name } }))
    } catch {
      setUploads((u) => ({ ...u, [category]: { status: 'error' } }))
    }
  }, [])

  const anyUploading = Object.values(uploads).some((u) => u.status === 'uploading')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const attachments = FILE_SLOTS
      .filter((s) => uploads[s.category].status === 'done')
      .map((s) => ({
        category: s.category,
        file_url: (uploads[s.category] as { status: 'done'; fileUrl: string }).fileUrl,
      }))
    onSubmit({
      vehicle_id: vehicleId,
      driver_id: driverId || undefined,
      datetime,
      location: location || undefined,
      description: description || undefined,
      another_driver_licensing_plate: otherPlate || undefined,
      another_driver_phone_number: otherPhone || undefined,
      another_driver_id_number: otherId || undefined,
      attachments,
    })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,.55)' }}
    >
      <div
        className="bg-raised border border-line rounded-2xl w-full overflow-y-auto"
        style={{ maxWidth: 600, maxHeight: '90vh', padding: '24px 26px' }}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-[17px] font-bold">הוספת תאונה</h2>
          <button onClick={onClose} className="text-faint hover:text-ink">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* vehicle */}
          <div>
            <label className="text-[12px] text-faint block mb-1">רכב *</label>
            <select
              value={vehicleId}
              onChange={(e) => setVehicleId(e.target.value)}
              required
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
              style={{ padding: '9px 12px' }}
            >
              <option value="">-- בחר רכב --</option>
              {vehicles.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.plate} - {v.make} {v.model}
                </option>
              ))}
            </select>
          </div>

          {/* driver */}
          <div>
            <label className="text-[12px] text-faint block mb-1">נהג</label>
            <select
              value={driverId}
              onChange={(e) => setDriverId(e.target.value)}
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
              style={{ padding: '9px 12px' }}
            >
              <option value="">-- ללא נהג --</option>
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          {/* datetime */}
          <div>
            <label className="text-[12px] text-faint block mb-1">תאריך ושעה *</label>
            <input
              type="datetime-local"
              value={datetime}
              onChange={(e) => setDatetime(e.target.value)}
              required
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold ltr"
              style={{ padding: '9px 12px' }}
            />
          </div>

          {/* location */}
          <div>
            <label className="text-[12px] text-faint block mb-1">מיקום</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
              style={{ padding: '9px 12px' }}
            />
          </div>

          {/* description */}
          <div>
            <label className="text-[12px] text-faint block mb-1">תיאור</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
              style={{ padding: '9px 12px' }}
            />
          </div>

          <hr className="border-line" />
          <div className="text-[12px] font-semibold text-muted">פרטי הצד השני</div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[12px] text-faint block mb-1">לוחית</label>
              <input
                type="text"
                value={otherPlate}
                onChange={(e) => setOtherPlate(e.target.value)}
                className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold ltr"
                style={{ padding: '9px 12px' }}
              />
            </div>
            <div>
              <label className="text-[12px] text-faint block mb-1">טלפון</label>
              <input
                type="text"
                value={otherPhone}
                onChange={(e) => setOtherPhone(e.target.value)}
                className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold ltr"
                style={{ padding: '9px 12px' }}
              />
            </div>
            <div>
              <label className="text-[12px] text-faint block mb-1">ת.ז.</label>
              <input
                type="text"
                value={otherId}
                onChange={(e) => setOtherId(e.target.value)}
                className="w-full bg-panel border border-control rounded-lg text-[13px] font-semibold"
                style={{ padding: '9px 12px' }}
              />
            </div>
          </div>

          <hr className="border-line" />
          <div className="text-[12px] font-semibold text-muted">קבצים מצורפים (אופציונלי)</div>

          <div className="flex flex-col gap-2">
            {FILE_SLOTS.map((slot) => {
              const state = uploads[slot.category]
              return (
                <div key={slot.category}>
                  <div className="text-[11px] text-faint mb-1">{slot.label}</div>
                  <div
                    className="border border-dashed border-control rounded-lg text-center text-[12px] text-faint cursor-pointer hover:border-[#2b3550] relative"
                    style={{ padding: '10px 14px' }}
                    onClick={() => inputRefs.current[slot.category]?.click()}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault()
                      const f = e.dataTransfer.files[0]
                      if (f) handleFile(slot.category, f)
                    }}
                  >
                    {state.status === 'idle' && (
                      <span>
                        גרור או <b>בחר קובץ</b>
                      </span>
                    )}
                    {state.status === 'uploading' && (
                      <span className="flex items-center justify-center gap-1">
                        <Loader2 size={13} className="animate-spin" />
                        מעלה…
                      </span>
                    )}
                    {state.status === 'done' && (
                      <span className="flex items-center justify-center gap-1 text-emerald-400">
                        <CheckCircle size={13} />
                        {(state as { fileName: string }).fileName}
                      </span>
                    )}
                    {state.status === 'error' && (
                      <span className="flex items-center justify-center gap-1 text-amber-400">
                        <AlertCircle size={13} />
                        שגיאה - נסה שוב
                      </span>
                    )}
                    <input
                      ref={(el) => { inputRefs.current[slot.category] = el }}
                      type="file"
                      accept={slot.accept}
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0]
                        if (f) handleFile(slot.category, f)
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              type="submit"
              className="flex-1"
              disabled={submitting || anyUploading}
            >
              {submitting ? 'שומר…' : 'הוסף תאונה'}
            </Button>
            <Button type="button" variant="secondary" onClick={onClose}>
              ביטול
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd services/webui && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add services/webui/package.json \
        services/webui/package-lock.json \
        services/webui/app/api/accident-upload/route.ts \
        services/webui/components/AccidentCard.tsx \
        services/webui/components/AccidentFormModal.tsx
git commit -m "add accident upload route, AccidentCard, AccidentFormModal"
```

---

### Task 4: webui - hook + page + sidebar

**Files:**
- Create: `services/webui/hooks/useAccidents.ts`
- Create: `services/webui/app/(admin)/accidents/page.tsx`
- Modify: `services/webui/components/Sidebar.tsx`

**Interfaces:**
- Consumes: `fetchAccidents`, `createAccident` from `fleet.ts`; `toUiAccident` from `adapters.ts`; `useVehicles`, `useDrivers` hooks
- Produces: `useAccidents()` returning `{ accidents: UiAccident[], add: MutateFunction, adding: boolean }`

- [ ] **Step 1: Create useAccidents hook**

Create `services/webui/hooks/useAccidents.ts`:

```typescript
'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAccidents, createAccident } from '@/lib/api/fleet'
import { toUiAccident } from '@/lib/adapters'
import { useVehicles } from './useVehicles'
import { useDrivers } from './useDrivers'
import type { UiAccident, AccidentCreate } from '@/lib/api/schemas'

const KEY = ['accidents']

export function useAccidents() {
  const qc = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: fetchAccidents })
  const { vehicles } = useVehicles()
  const { drivers } = useDrivers()

  const vehicleById = Object.fromEntries(vehicles.map((v) => [v.id, v]))
  const driverById = Object.fromEntries(drivers.map((d) => [d.id, d]))

  const add = useMutation({
    mutationFn: createAccident,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const accidents: UiAccident[] = (query.data ?? []).map((a) =>
    toUiAccident(a, vehicleById, driverById),
  )

  return {
    accidents,
    loading: query.isLoading,
    add: add.mutate,
    adding: add.isPending,
  }
}
```

- [ ] **Step 2: Create accidents page**

Create `services/webui/app/(admin)/accidents/page.tsx`:

```typescript
'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useAccidents } from '@/hooks/useAccidents'
import { useVehicles } from '@/hooks/useVehicles'
import { useDrivers } from '@/hooks/useDrivers'
import { Button } from '@/components/ui/button'
import { AccidentCard } from '@/components/AccidentCard'
import { AccidentFormModal } from '@/components/AccidentFormModal'
import type { AccidentCreate } from '@/lib/api/schemas'

export default function AccidentsPage() {
  const { accidents, add, adding } = useAccidents()
  const { vehicles } = useVehicles()
  const { drivers } = useDrivers()
  const [showForm, setShowForm] = useState(false)

  const handleSubmit = (payload: AccidentCreate) => {
    add(payload)
    setShowForm(false)
  }

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between gap-4 mb-[18px] flex-wrap">
        <div />
        <Button onClick={() => setShowForm(true)}>
          <Plus size={16} strokeWidth={2.4} />
          הוסף תאונה
        </Button>
      </div>

      <div
        className="grid gap-[15px]"
        style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(330px,1fr))' }}
      >
        {accidents.map((a) => (
          <AccidentCard key={a.id} a={a} />
        ))}
      </div>

      {showForm && (
        <AccidentFormModal
          vehicles={vehicles}
          drivers={drivers}
          onSubmit={handleSubmit}
          onClose={() => setShowForm(false)}
          submitting={adding}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 3: Add accidents nav item to Sidebar**

In `services/webui/components/Sidebar.tsx`:

**3a.** Add `ShieldAlert` to the lucide-react import:

```typescript
import {
  LayoutDashboard,
  Truck,
  User,
  Building2,
  TriangleAlert,
  CalendarCheck,
  Wrench,
  Settings,
  MessageSquare,
  Activity,
  LogOut,
  Bot,
  ShieldAlert,        // NEW
  type LucideIcon,
} from 'lucide-react'
```

**3b.** Add `'accidents'` to the `NavItem` badge union type:

```typescript
type NavItem = { href: string; label: string; Icon: LucideIcon; badge?: 'vehicles' | 'drivers' | 'customers' | 'events' | 'accidents'; statusDot?: boolean }
```

**3c.** Add the nav entry to `NAV` after the events entry:

```typescript
const NAV: NavItem[] = [
  { href: '/dashboard',         label: 'לוח בקרה',    Icon: LayoutDashboard },
  { href: '/vehicles',          label: 'רכבים',        Icon: Truck,         badge: 'vehicles' },
  { href: '/drivers',           label: 'נהגים',        Icon: User,          badge: 'drivers' },
  { href: '/customers',         label: 'לקוחות',       Icon: Building2,     badge: 'customers' },
  { href: '/events',            label: 'משימות',       Icon: TriangleAlert, badge: 'events' },
  { href: '/accidents',         label: 'תאונות',       Icon: ShieldAlert,   badge: 'accidents' },  // NEW
  { href: '/attendance',        label: 'נוכחות',       Icon: CalendarCheck },
  { href: '/bot',               label: 'ניהול בוט',   Icon: Bot },
  { href: '/maintenance-types', label: 'סוגי טיפול',  Icon: Wrench },
  { href: '/config',            label: 'הגדרות',       Icon: Settings },
  { href: '/health',            label: 'מצב מערכת',   Icon: Activity,      statusDot: true },
  { href: '/chat',              label: 'צ׳אט ועוזר',  Icon: MessageSquare },
]
```

**3d.** Add accidents hook import + count to the Sidebar component body:

Add import:
```typescript
import { useAccidents } from '@/hooks/useAccidents'
```

In `Sidebar` function body, add after the `useEvents` call:
```typescript
const { accidents } = useAccidents()
```

In the `counts` object, add `accidents`:
```typescript
const counts: Record<string, number> = {
  vehicles: vehicles.length,
  drivers: drivers.length,
  customers: customers.length,
  events: openCount(events),
  accidents: accidents.length,
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd services/webui && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add services/webui/hooks/useAccidents.ts \
        services/webui/app/\(admin\)/accidents/page.tsx \
        services/webui/components/Sidebar.tsx
git commit -m "add accidents page, useAccidents hook, sidebar nav entry"
```
