# Context: Shepherd

Glossary of the domain language. Terms here are canonical - code, docs, and UI
should use them consistently.

## Tenancy

- **Company** - a tenant. The top-level unit of data isolation; every domain
  record belongs to exactly one company.

## Personas (who acts on the system)

- **System Admin** - the platform operator (e.g. the Shepherd team). Sits
  *above* companies: cross-company, belongs to no single company. The same
  identity in the web console and the Telegram bot. Manages companies and
  logins, and can debug a company by impersonating one of its users.
- **Company Admin** - an administrator scoped to one company. Manages and reads
  only that company's fleet, drivers, customers, attendance, and bot users.
  (In the Telegram bot this is the persona the existing "admin" menu serves.)
- **Driver** - operates within one company; reports issues/accidents, updates
  their own details, and (when the company enables it) clocks in/out.

## System-admin capabilities

A System Admin has three capabilities in the Telegram bot:

- **System overview** - a read-only, cross-company high-level view (per-company
  health and counts). No mutation.
- **Debug mode** - a sandbox. The System Admin plays as a **Driver** or a
  **Company Admin** inside the **Playground company**. Because that company is
  internal mock data, actions are unguarded and not audited - it exists to
  experience the real persona flows safely.
- **Customer Live mode** - the System Admin selects a real customer
  (**Company**), then acts as one of its **Company Admins** or one of its
  **Drivers**, operating on real data. Guarded: a persistent "acting as" banner,
  a confirmation on destructive actions, and an audit trail.

Supporting terms:

- **Playground company** - a single built-in, *internal* company holding mock
  drivers/vehicles, used only by Debug mode. Never a real customer; excluded
  from customer-facing lists and from the System overview's customer counts.
- **Impersonation session** - a Customer-Live act-as period. Audited (operator,
  company, effective persona, start/stop, and each confirmed write) for
  cross-tenant accountability. Debug mode is not audited.
- **Effective persona** vs **operator** - the persona being acted as vs the
  System Admin behind it. The audit ties every Customer-Live action back to the
  operator.

## Fleet

- **Vehicle** - a car in a company's fleet. May be assigned to one Driver
  (`driver_id`) and may reference one maintenance type.
- **Maintenance type (cycle)** - an ordered list of service **care** steps plus
  a km and/or month interval. A vehicle's next-due care is derived from the last
  care done, wrapping around the cycle after the final step.
- **Care** - one service step in a maintenance cycle.
  - **Back-filling the cycle position** on vehicle add/edit records a *past*
    service (`last_maintenance_km`/date): its km may not exceed the vehicle's
    `current_km` (equal allowed) and its date may not be in the future. It
    recomputes the next-due care/km/date without writing a service record.
  - **Logging a live care** (`POST /vehicle_care`) records a service happening
    now: `km_at_service` is a fresh odometer reading, so it may not be *below*
    `current_km` (no downgrade) and it advances `current_km` to that value; the
    service date may not be in the future.
  - The odometer (`current_km`) only ever increases - the same rule the KM
    update flow enforces.
