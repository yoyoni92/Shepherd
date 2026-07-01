# Design: set a vehicle's maintenance-cycle position on add/edit

Date: 2026-07-01

## Problem

A **maintenance type** is a *cycle*: an ordered list of unique service-step
labels (its `steps`, e.g. `["oil", "brakes", "timing belt"]`) plus a km and/or
month interval. A `Vehicle` references one maintenance type, and its next-due
step is derived from `Vehicle.last_maintenance_type` by `next_maintenance()`
(`db/shepherd_db/logic.py`), which wraps around the cycle.

When `last_maintenance_type` is unset, `next_maintenance()` always returns
`steps[0]`. But the **add-vehicle path** (`VehicleCreate` schema, `POST
/vehicles`, and the WebUI add form) has **no field for the cycle position**, and
neither does the edit path (`VehicleUpdate`). So every car is assumed to start at
the beginning of its maintenance cycle.

Real fleets add cars that are already partway through their cycle. If a cycle has
three "cares" (steps), the admin must be able to say which one the car is
currently on, per car - otherwise the next-due service is computed wrongly.

## Goal

When an admin adds or edits a car that has a maintenance type, let them set the
car's current position in that cycle by choosing the **last-done care** (one of
the cycle's steps) and, optionally, the **km** and **date** it was done. The
system derives the next-due step, km, and date from that.

This is a **pointer-set**, not a retroactive service log: no `VehicleCare` row is
created and no maintenance events are mutated.

## Non-goals

- No Telegram bot surface (there is no add/edit-vehicle flow in the bot).
- No assignment/rotation of cars between drivers ("current car" as a driver's
  active vehicle is out of scope; that is `Vehicle.driver_id`, unchanged).
- No maintenance-history table. Setting position only writes the `last_*` /
  `next_*` fields already on `Vehicle`.

## Data model

No schema change. Storage already exists on `Vehicle` (`db/shepherd_db/models.py`):

- Input: `last_maintenance_type` (Text, free-text step label), `last_maintenance_km`
  (int), `last_maintenance_date` (date).
- Derived: `next_maintenance_type` (Text), `next_maintenance_km` (int),
  `next_maintenance_date` (date).

## Behavior

When `last_maintenance_type` is provided on create or update **and** the vehicle
has a maintenance type, the Fleet API:

1. Reads the maintenance type's `steps`, `interval_km`, `interval_months`.
2. Calls `next_maintenance(last_step=last_maintenance_type, steps=...,
   last_km=last_maintenance_km or 0, interval_km=..., last_date=last_maintenance_date,
   interval_months=...)`.
3. Writes `last_maintenance_type/_km/_date` from the input and
   `next_maintenance_type/_km/_date` from the result.

This mirrors the derivation in `repo.create_care` (`repo.py:313-332`), **without**
its `VehicleCare` insert or its open-`maintenance_due`-event resolution.

If `last_maintenance_type` is not provided, behavior is unchanged (next-due
defaults to `steps[0]` when first computed).

## Fleet API changes

### `services/fleet-api/app/schemas.py`

Add to both `VehicleCreate` and `VehicleUpdate`:

```python
last_maintenance_type: str | None = None
last_maintenance_km: int | None = None
last_maintenance_date: date | None = None
```

`VehicleRead` already exposes `last_maintenance_type/_km/_date` and
`next_maintenance_type/_km/_date` - no change.

### `services/fleet-api/app/repo.py`

- Add a helper `apply_cycle_position(vehicle)` that performs steps 1-3 above,
  reading `vehicle.maintenance_type`. Reused by create and update.
- `create_vehicle`: after `session.add(vehicle)` / `flush`, if
  `vehicle.last_maintenance_type` is set, call the helper before commit.
- `update_vehicle`: after applying the patch, if the patch set
  `last_maintenance_type`, call the helper before commit. (The maintenance type
  may be one already on the vehicle or set in the same patch.)

### `services/fleet-api/app/routers/vehicles.py`

Validation in `create_vehicle` and `update_vehicle` before persisting: if
`last_maintenance_type` is provided,

- 400 if the (resulting) vehicle has no maintenance type, and
- 400 if `last_maintenance_type` is not one of that type's `steps`.

This prevents `next_maintenance()` silently treating an unknown step as
"never serviced" and returning `steps[0]`.

## WebUI changes

### Dependent field options in the shared modal

`components/EntityFormModal.tsx`: allow `FieldDef.options` to be either the
current static array **or** a function `(values: FormValues) => { value: string;
label: string }[]`, evaluated against live form state on each render. The select
resolves options by calling the function when it is one. Small, generic change;
no behavior change for existing static-option fields.

### Vehicle form

`app/(admin)/vehicles/page.tsx`:

- Add three fields to `formFields`:
  - `last_maintenance_type` - `select`, options derived from the currently
    selected `maintenance_type_id` via the new function form: the steps of that
    maintenance type. Empty when no maintenance type is selected.
  - `last_maintenance_km` - `number`, optional, `nonNegInt` validation.
  - `last_maintenance_date` - `date`, optional.
- `editInitial`: seed these from the existing vehicle (`last_maintenance_type`,
  `last_maintenance_km`, `last_maintenance_date`).
- `toPayload`: send them only when non-empty (km coerced to `Number`).

### Maintenance-type steps client-side

The step dropdown needs each maintenance type's `steps`. Extend
`hooks/useMaintenanceTypes` (and the `lib/api` type/mapping it uses) so the steps
array is available in the page, keyed by maintenance-type id, to build the
options function.

### TS types

`lib/api/schemas.ts` (`VehicleCreate` and the UI vehicle type) gain the three
fields so `toPayload` / `editInitial` type-check.

## Testing

Fleet API (pytest):

- Create with a maintenance type + `last_maintenance_type` set to the 2nd of 3
  steps derives `next_maintenance_type` = 3rd step (and `next_km` from
  `last_km + interval_km` when km given).
- Create without `last_maintenance_type` leaves next-due defaulting to `steps[0]`
  behavior unchanged.
- Update setting `last_maintenance_type` recomputes the `next_*` fields.
- 400 when `last_maintenance_type` is set but the vehicle has no maintenance type.
- 400 when `last_maintenance_type` is not in the type's `steps`.
- No `VehicleCare` row is created and no events are mutated by any of the above.

WebUI (if the project has form tests): the step dropdown lists the selected
maintenance type's steps and is empty when none is selected.

## Docs to update in the implementing commits

- `CONTEXT.md` - if we choose to formalize "vehicle" / "maintenance cycle" /
  "care" terms (currently undefined there).
- Fleet API service `README.md` / OpenAPI description if the create/update
  contract summary is documented there.
- `.env.example` - no impact (no new config).
