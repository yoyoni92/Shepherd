# Vehicle Maintenance-Cycle Position Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an admin set a car's current position in its maintenance cycle (which "care" step was last done, plus optional km/date) when adding or editing the car, so the next-due service is computed from that position instead of always defaulting to the first step.

**Architecture:** No DB change - `Vehicle` already stores `last_maintenance_type/_km/_date` and derived `next_maintenance_type/_km/_date`. A shared repo helper `apply_cycle_position(vehicle)` recomputes the `next_*` fields from the vehicle's `last_*` fields via the existing `next_maintenance()` cycle logic; `create_vehicle`, `update_vehicle`, and (refactored) `create_care` all route through it. The WebUI gains a last-done-care dropdown whose options are the selected maintenance type's steps, enabled by teaching the shared `EntityFormModal` to accept function-valued field options.

**Tech Stack:** Python / FastAPI / SQLAlchemy / pytest (fleet-api); Next.js / React / TypeScript / Zod / vitest + @testing-library/react (webui).

## Global Constraints

- No DB migrations - schema is rebuilt from models; do not add columns (all needed columns already exist).
- Domain term for a service step is a **care**; the cycle is the maintenance type's ordered `steps`.
- This is a pointer-set, not a service log: setting position must NOT create a `VehicleCare` row and must NOT mutate maintenance events.
- Telegram bot is out of scope (it has no add/edit-vehicle flow).
- Ponytail: reuse the existing `next_maintenance()` math; do not duplicate the cycle logic.

---

### Task 1: Backend - derive cycle position on vehicle create

**Files:**
- Modify: `services/fleet-api/app/schemas.py` (`VehicleCreate`, ~line 21-33)
- Modify: `services/fleet-api/app/repo.py` (add `apply_cycle_position`; refactor `create_care` ~313-332; call from `create_vehicle` ~65-70)
- Modify: `services/fleet-api/app/routers/vehicles.py` (`create_vehicle` ~84-101; add validation helper)
- Test: `services/fleet-api/tests/test_vehicles.py`

**Interfaces:**
- Produces: `repo.apply_cycle_position(vehicle: Vehicle) -> dict` - reads `vehicle.last_maintenance_type/_km/_date` and `vehicle.maintenance_type`, sets `vehicle.next_maintenance_type/_km/_date`, returns the `next_maintenance()` dict `{"next_type", "next_km", "next_date"}`.
- Produces: `VehicleCreate` fields `last_maintenance_type: str | None`, `last_maintenance_km: int | None`, `last_maintenance_date: date | None`.

- [ ] **Step 1: Write the failing tests**

Add to `services/fleet-api/tests/test_vehicles.py` (reuse `admin_headers` already imported; `uuid` already imported):

```python
def _make_cycle(client, steps, interval_km=10000):
    r = client.post(
        "/maintenance-types",
        json={"name": f"cyc-{uuid.uuid4().hex[:6]}", "interval_km": interval_km, "steps": steps},
        headers=admin_headers(),
    )
    return r.json()["id"]


def test_create_vehicle_with_cycle_position_derives_next(client):
    mt = _make_cycle(client, ["small", "big", "huge"])
    r = client.post(
        "/vehicles",
        json={
            "licensing_plate": _plate(uuid.uuid4().hex[:6]),
            "maintenance_type_id": mt,
            "last_maintenance_type": "big",
            "last_maintenance_km": 50000,
        },
        headers=admin_headers(),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["last_maintenance_type"] == "big"
    assert data["next_maintenance_type"] == "huge"      # step after "big"
    assert data["next_maintenance_km"] == 60000          # 50000 + 10000 interval


def test_create_vehicle_without_position_leaves_next_unset(client):
    mt = _make_cycle(client, ["small", "big"])
    r = client.post(
        "/vehicles",
        json={"licensing_plate": _plate(uuid.uuid4().hex[:6]), "maintenance_type_id": mt},
        headers=admin_headers(),
    )
    assert r.status_code == 201
    assert r.json()["next_maintenance_type"] is None     # unchanged behavior


def test_create_vehicle_position_without_maintenance_type_400(client):
    r = client.post(
        "/vehicles",
        json={"licensing_plate": _plate(uuid.uuid4().hex[:6]), "last_maintenance_type": "big"},
        headers=admin_headers(),
    )
    assert r.status_code == 400


def test_create_vehicle_position_not_in_cycle_400(client):
    mt = _make_cycle(client, ["small", "big"])
    r = client.post(
        "/vehicles",
        json={
            "licensing_plate": _plate(uuid.uuid4().hex[:6]),
            "maintenance_type_id": mt,
            "last_maintenance_type": "nope",
        },
        headers=admin_headers(),
    )
    assert r.status_code == 400
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd services/fleet-api && python -m pytest tests/test_vehicles.py -k cycle_position -v`
Expected: FAIL - `last_maintenance_type` is rejected/ignored by `VehicleCreate` (unexpected keyword) and `next_maintenance_type` stays `None`; the 400 tests get 201.

- [ ] **Step 3: Add the schema fields**

In `services/fleet-api/app/schemas.py`, add to `VehicleCreate` (keep `date` import already present at top of file):

```python
    last_maintenance_type: str | None = None
    last_maintenance_km: int | None = None
    last_maintenance_date: date | None = None
```

- [ ] **Step 4: Add the shared helper and route create through it**

In `services/fleet-api/app/repo.py`, add the helper just above `create_vehicle` (~line 64):

```python
def apply_cycle_position(vehicle: Vehicle) -> dict:
    """Recompute next_* service fields from the vehicle's last_maintenance_* and its cycle.

    Pointer-set only: writes next_maintenance_type/_km/_date on the vehicle and returns the
    next_maintenance() result. Does not create care rows or touch events.
    """
    mtype = vehicle.maintenance_type
    steps = mtype.steps if mtype else [vehicle.last_maintenance_type]
    interval_km = mtype.interval_km if mtype else 10_000
    interval_months = mtype.interval_months if mtype else None
    nm = next_maintenance(
        vehicle.last_maintenance_type,
        steps,
        last_km=vehicle.last_maintenance_km or 0,
        interval_km=interval_km,
        last_date=vehicle.last_maintenance_date,
        interval_months=interval_months,
    )
    vehicle.next_maintenance_km = nm["next_km"]
    vehicle.next_maintenance_date = nm["next_date"]
    vehicle.next_maintenance_type = nm["next_type"]
    return nm
```

Change `create_vehicle` to derive when a position was given:

```python
def create_vehicle(session: Session, data: dict) -> Vehicle:
    vehicle = Vehicle(**data)
    session.add(vehicle)
    session.flush()
    if vehicle.last_maintenance_type is not None:
        apply_cycle_position(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle
```

Refactor `create_care` (lines ~313-332) to reuse the helper - replace the inline `mtype/steps/interval/nm` block and the three `vehicle.next_*` assignments with:

```python
    vehicle.last_maintenance_date = care.service_date
    vehicle.last_maintenance_type = care.maintenance_type
    vehicle.last_maintenance_km = care.km_at_service
    nm = apply_cycle_position(vehicle)
```

(Leave the open-`maintenance_due`-event resolution loop and the `care._next_*` attribute attachment below it untouched - they still use `nm`.)

- [ ] **Step 5: Add router validation on create**

In `services/fleet-api/app/routers/vehicles.py`, add a module-level helper and call it in `create_vehicle` before `repo.create_vehicle`:

```python
def _validate_cycle_position(session, last_step, maintenance_type_id):
    if last_step is None:
        return
    if maintenance_type_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="last_maintenance_type requires a maintenance_type_id")
    mtype = repo.get_maintenance_type(session, maintenance_type_id)
    if mtype is None or last_step not in mtype.steps:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="last_maintenance_type is not a step of the maintenance cycle")
```

In `create_vehicle`, after the duplicate-plate check and before `data = body.model_dump()`:

```python
    _validate_cycle_position(session, body.last_maintenance_type, body.maintenance_type_id)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd services/fleet-api && python -m pytest tests/test_vehicles.py tests/test_care.py -v`
Expected: PASS - new cycle-position tests pass; all existing `test_care.py` tests (cycle advancement regression guard) still pass.

- [ ] **Step 7: Commit**

```bash
git add services/fleet-api/app/schemas.py services/fleet-api/app/repo.py \
        services/fleet-api/app/routers/vehicles.py services/fleet-api/tests/test_vehicles.py
git commit -m "derive vehicle maintenance-cycle position on create"
```

---

### Task 2: Backend - derive cycle position on vehicle edit

**Files:**
- Modify: `services/fleet-api/app/schemas.py` (`VehicleUpdate`, ~line 36-49)
- Modify: `services/fleet-api/app/repo.py` (`update_vehicle` ~73-81)
- Modify: `services/fleet-api/app/routers/vehicles.py` (`update_vehicle` ~104-119)
- Test: `services/fleet-api/tests/test_vehicles.py`

**Interfaces:**
- Consumes: `repo.apply_cycle_position` and `_validate_cycle_position` from Task 1.
- Produces: `VehicleUpdate` fields `last_maintenance_type`, `last_maintenance_km`, `last_maintenance_date` (all optional).

- [ ] **Step 1: Write the failing tests**

Add to `services/fleet-api/tests/test_vehicles.py`:

```python
def test_update_vehicle_sets_cycle_position(client):
    mt = _make_cycle(client, ["small", "big", "huge"])
    plate = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": plate, "maintenance_type_id": mt},
                headers=admin_headers())
    r = client.patch(
        f"/vehicles/{plate}",
        json={"last_maintenance_type": "small", "last_maintenance_km": 10000},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["next_maintenance_type"] == "big"        # step after "small"
    assert data["next_maintenance_km"] == 20000


def test_update_vehicle_position_not_in_cycle_400(client):
    mt = _make_cycle(client, ["small", "big"])
    plate = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": plate, "maintenance_type_id": mt},
                headers=admin_headers())
    r = client.patch(f"/vehicles/{plate}", json={"last_maintenance_type": "nope"},
                     headers=admin_headers())
    assert r.status_code == 400
```

Note: `PATCH /vehicles/{plate}` - the existing update test in this file already PATCHes by plate; confirm the route param and mirror it. If the route is by `vehicle_id`, capture the id from the create response and use that instead.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd services/fleet-api && python -m pytest tests/test_vehicles.py -k "update_vehicle and cycle or update_vehicle_position" -v`
Expected: FAIL - `VehicleUpdate` ignores `last_maintenance_type`; `next_maintenance_type` unchanged; 400 test returns 200.

- [ ] **Step 3: Add the schema fields**

In `services/fleet-api/app/schemas.py`, add to `VehicleUpdate`:

```python
    last_maintenance_type: str | None = None
    last_maintenance_km: int | None = None
    last_maintenance_date: date | None = None
```

- [ ] **Step 4: Recompute on update in the repo**

In `services/fleet-api/app/repo.py`, change `update_vehicle` to recompute when the position step was part of the patch:

```python
def update_vehicle(session: Session, vehicle_id: UUID, data: dict) -> Vehicle | None:
    vehicle = session.get(Vehicle, vehicle_id)
    if vehicle is None:
        return None
    for key, value in data.items():
        setattr(vehicle, key, value)
    session.flush()
    if "last_maintenance_type" in data and vehicle.last_maintenance_type is not None:
        apply_cycle_position(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle
```

- [ ] **Step 5: Add router validation on update**

In `services/fleet-api/app/routers/vehicles.py` `update_vehicle`, after `assert_company(existing, caller)` and before `repo.update_vehicle`:

```python
    if body.last_maintenance_type is not None:
        mtype_id = body.maintenance_type_id or existing.maintenance_type_id
        _validate_cycle_position(session, body.last_maintenance_type, mtype_id)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd services/fleet-api && python -m pytest tests/test_vehicles.py tests/test_care.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add services/fleet-api/app/schemas.py services/fleet-api/app/repo.py \
        services/fleet-api/app/routers/vehicles.py services/fleet-api/tests/test_vehicles.py
git commit -m "derive vehicle maintenance-cycle position on edit"
```

---

### Task 3: WebUI - function-valued field options in EntityFormModal

**Files:**
- Modify: `services/webui/components/EntityFormModal.tsx` (`FieldDef`, ~line 9-19; select render, ~line 87-101)
- Test: `services/webui/tests/EntityFormModal.test.tsx` (create)

**Interfaces:**
- Produces: `FieldDef.options?: Opt[] | ((values: FormValues) => Opt[])` where `Opt = { value: string; label: string }`. When a function, it is evaluated against the live form `values` on each render to produce the select's options.

- [ ] **Step 1: Write the failing test**

Create `services/webui/tests/EntityFormModal.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { EntityFormModal, type FieldDef } from '@/components/EntityFormModal'

const fields: FieldDef[] = [
  { key: 'type', label: 'Type', type: 'select', options: [{ value: 't1', label: 'One' }] },
  {
    key: 'step',
    label: 'Step',
    type: 'select',
    options: (v) => (v.type === 't1' ? [{ value: 's1', label: 'Step A' }] : []),
  },
]

test('function-valued options resolve from live form values', () => {
  render(
    <EntityFormModal title="t" fields={fields} submitLabel="ok" onSubmit={() => {}} onClose={() => {}} />,
  )
  // Before selecting a type, the dependent select has no data option.
  expect(screen.queryByRole('option', { name: 'Step A' })).toBeNull()
  fireEvent.change(screen.getByLabelText('Type'), { target: { value: 't1' } })
  expect(screen.getByRole('option', { name: 'Step A' })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd services/webui && npx vitest run tests/EntityFormModal.test.tsx`
Expected: FAIL - `f.options?.map` treats the function as a non-array; "Step A" never renders.

- [ ] **Step 3: Implement function-valued options**

In `services/webui/components/EntityFormModal.tsx`, update the type (line ~14):

```tsx
  options?: { value: string; label: string }[] | ((values: FormValues) => { value: string; label: string }[])
```

In the select render (line ~96), resolve options against current values:

```tsx
                    {(typeof f.options === 'function' ? f.options(values) : f.options)?.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
```

(`values` is already in scope in the component.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd services/webui && npx vitest run tests/EntityFormModal.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/webui/components/EntityFormModal.tsx services/webui/tests/EntityFormModal.test.tsx
git commit -m "support function-valued field options in EntityFormModal"
```

---

### Task 4: WebUI - last-done-care fields on the vehicle form

**Files:**
- Modify: `services/webui/lib/api/schemas.ts` (`VehicleCreateSchema` ~line 28-41; `UiVehicle` ~line 254-271)
- Modify: `services/webui/lib/adapters.ts` (`toUiVehicle`)
- Modify: `services/webui/app/(admin)/vehicles/page.tsx` (`formFields`, `editInitial`, `toPayload`, and pass maintenance-type steps)
- Test: `services/webui/tests/vehicleStepOptions.test.ts` (create)

**Interfaces:**
- Consumes: `FieldDef.options` function form from Task 3; `UiMaintenanceType.steps` (already exists); backend fields from Tasks 1-2.
- Produces: pure helper `stepOptions(types: UiMaintenanceType[], maintenanceTypeId: string) => { value: string; label: string }[]` in `vehicles/page.tsx`, exported for test.

- [ ] **Step 1: Write the failing test**

Create `services/webui/tests/vehicleStepOptions.test.ts`:

```ts
import { stepOptions } from '@/app/(admin)/vehicles/page'
import type { UiMaintenanceType } from '@/lib/api/schemas'

const types: UiMaintenanceType[] = [
  { id: 'm1', name: 'A', description: null, intervalKm: 10000, intervalMonths: null, steps: ['small', 'big', 'huge'] },
]

test('stepOptions lists the selected cycle steps', () => {
  expect(stepOptions(types, 'm1').map((o) => o.value)).toEqual(['small', 'big', 'huge'])
})

test('stepOptions is empty when no maintenance type is selected', () => {
  expect(stepOptions(types, '')).toEqual([])
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd services/webui && npx vitest run tests/vehicleStepOptions.test.ts`
Expected: FAIL - `stepOptions` is not exported from the page.

- [ ] **Step 3: Extend TS types and adapter**

In `services/webui/lib/api/schemas.ts`, add to `VehicleCreateSchema` (after `maintenance_type_id`):

```ts
  last_maintenance_type: z.string().nullish(),
  last_maintenance_km: z.number().nullish(),
  last_maintenance_date: z.string().nullish(),
```

Add to the `UiVehicle` interface (after `nextMaintenanceType`):

```ts
  lastMaintenanceType: string | null
  lastMaintenanceKm: number | null
```

(`lastService` already carries `last_maintenance_date`.)

In `services/webui/lib/adapters.ts` `toUiVehicle`, add:

```ts
    lastMaintenanceType: v.last_maintenance_type ?? null,
    lastMaintenanceKm: v.last_maintenance_km ?? null,
```

- [ ] **Step 4: Add the pure step-options helper and wire the form**

In `services/webui/app/(admin)/vehicles/page.tsx`:

Export the helper (top level, after imports):

```tsx
export const stepOptions = (types: UiMaintenanceType[], maintenanceTypeId: string) =>
  (types.find((t) => t.id === maintenanceTypeId)?.steps ?? []).map((s) => ({ value: s, label: s }))
```

Import the type: add `UiMaintenanceType` to the existing `import type { ... } from '@/lib/api/schemas'` line.

Add fields to `formFields` (which must now receive the maintenance types). Change its signature to accept `maintenanceTypes: UiMaintenanceType[]` and add, right after the `maintenance_type_id` field:

```tsx
  { key: 'last_maintenance_type', label: 'טיפול אחרון שבוצע', type: 'select', options: (v) => stepOptions(maintenanceTypes, v.maintenance_type_id) },
  { key: 'last_maintenance_km', label: 'ק״מ בטיפול האחרון', type: 'number', validate: nonNegInt },
  { key: 'last_maintenance_date', label: 'תאריך טיפול אחרון', type: 'date' },
```

Update the `fields = formFields(...)` call in the component to pass `maintenanceTypes` (the `maintenanceOpts` arg stays for the `maintenance_type_id` select).

Add to `editInitial`:

```tsx
  last_maintenance_type: v.lastMaintenanceType ?? '',
  last_maintenance_km: v.lastMaintenanceKm != null ? String(v.lastMaintenanceKm) : '',
  last_maintenance_date: v.lastService ?? '',
```

Add to `toPayload` (before `return`):

```ts
  put('last_maintenance_type', values.last_maintenance_type)
  if (values.last_maintenance_km.trim()) out.last_maintenance_km = Number(values.last_maintenance_km)
  put('last_maintenance_date', values.last_maintenance_date)
```

- [ ] **Step 5: Run the test and typecheck to verify they pass**

Run: `cd services/webui && npx vitest run tests/vehicleStepOptions.test.ts && npx tsc --noEmit`
Expected: PASS and no type errors.

- [ ] **Step 6: Commit**

```bash
git add services/webui/lib/api/schemas.ts services/webui/lib/adapters.ts \
        "services/webui/app/(admin)/vehicles/page.tsx" services/webui/tests/vehicleStepOptions.test.ts
git commit -m "add last-done-care fields to the vehicle add/edit form"
```

---

### Task 5: Docs sync

**Files:**
- Modify: `CONTEXT.md` (add vehicle / maintenance cycle / care terms)
- Modify: `services/fleet-api/README.md` (if it documents the vehicle create/update contract)

- [ ] **Step 1: Add domain terms to CONTEXT.md**

Under a suitable section, add concise glossary entries (canonical language):

```markdown
## Fleet

- **Vehicle** - a car in a company's fleet. May be assigned to one Driver
  (`driver_id`) and reference one maintenance type.
- **Maintenance type (cycle)** - an ordered list of service **care** steps plus
  a km and/or month interval. A vehicle's next-due care is derived from the last
  care done, wrapping around the cycle.
- **Care** - one service step in a maintenance cycle. Setting a vehicle's current
  care position (last-done care + optional km/date) recomputes its next-due
  service without logging a service record.
```

- [ ] **Step 2: Check the fleet-api README**

Run: `grep -n "vehicles\|maintenance" services/fleet-api/README.md`
If the create/update contract or fields are listed, add the three `last_maintenance_*` inputs; otherwise note "no doc impact" and skip.

- [ ] **Step 3: Commit**

```bash
git add CONTEXT.md services/fleet-api/README.md
git commit -m "document vehicle maintenance-cycle position feature"
```

---

## Self-Review

**Spec coverage:**
- API create fields + derivation → Task 1. API edit fields + derivation → Task 2. 400 validation (no type / step not in cycle) → Tasks 1 & 2. Pointer-set, no VehicleCare / no events → guaranteed by `apply_cycle_position` (no insert, no event code) and asserted implicitly by `test_care.py` still passing; Task 1 Step 6 runs it.
- WebUI dependent dropdown (#1) → Task 3 (modal) + Task 4 (form). km/date optional → Task 4. Steps available client-side → reuse `UiMaintenanceType.steps` (no fetch added).
- Docs → Task 5.

**Placeholder scan:** No TBD/TODO; every code step shows full code. The one conditional ("PATCH by plate vs id") is resolved by the note in Task 2 Step 1 pointing at the existing update test's route form.

**Type consistency:** `apply_cycle_position(vehicle) -> dict` used identically in Tasks 1-2. `stepOptions(types, id)` signature matches its test and its `formFields` call. `UiVehicle.lastMaintenanceType/lastMaintenanceKm` added in Task 4 and consumed in `editInitial` in the same task. `VehicleCreate` fields (Task 1) and `VehicleUpdate` fields (Task 2) match the TS `VehicleCreateSchema` additions (Task 4).
