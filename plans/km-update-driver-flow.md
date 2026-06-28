# Design: Update KM record from the bot (driver + admin)

**Status**: design (approved)
**Date**: 2026-06-28
**Services touched**: `telegram-bot`, `fleet-api`, `webui`

## Goal

Let a driver record a new odometer (KM) reading from the bot menu, and let a
company admin do the same for any vehicle in their fleet. Every reading is
validated against the current value and a sanity cap, and is tagged with a
`source` (`"telegram"` here; other sources come later).

## What already exists (no change)

- `POST /km` accepts `{vehicle_id, km, source}` and already persists `source`
  (`fleet-api/app/routers/km.py`, `schemas.KmUpdateRequest`).
- `Action.KM_UPDATE` already permits a driver to update their own assigned
  vehicle and an admin to update any vehicle in their company.
- The generic company-admin settings page (`webui/app/(admin)/config/page.tsx`)
  already edits per-company integer settings via a `FIELDS` list (it already
  contains `maintenance_km_buffer`), backed by the generic `/config/{key}`
  GET/PUT.

So the work is the bot flow, the validation, and one new configurable threshold
surfaced in the existing settings page.

## Decisions

### Validation (authoritative in fleet-api)

Enforced in the `/km` router before persisting, using the already-loaded
`vehicle`:

- **Floor**: reject if `body.km < vehicle.current_km` -> `422`,
  detail `"km_below_current"`.
- **Cap (max increase per update)**: reject if
  `body.km - vehicle.current_km > threshold` -> `422`,
  detail `"km_increment_too_large"`.
- If `vehicle.current_km is None` (never recorded), skip both checks - the first
  reading is unconstrained.
- `threshold` comes from a new repo helper `get_km_max_increment(session,
  company_id)`, **default 10000**, stored as SystemConfig key `km_max_increment`
  (mirrors `get_maintenance_buffer` / `maintenance_km_buffer`).

Distinct `detail` codes let the bot map each failure to the right Hebrew
message.

### Validation split (bot vs api)

- **Bot** validates *numeric format* and *floor* locally (it already fetches the
  vehicle's `current_km` to show it), for instant feedback.
- **API** is the source of truth and re-validates *floor + cap*.
- The **cap** is enforced only by the API and surfaced to the user via the mapped
  `422` message. The bot does NOT fetch the threshold itself: it is admin config
  and drivers lack `READ_CONFIG`, so pulling it into the bot would add coupling
  for marginal benefit.

### Configurable threshold in the settings UI

Add **one entry** to the existing `FIELDS` list in `config/page.tsx`:

```
{ key: 'km_max_increment', label: 'עליית ק״מ מרבית לעדכון',
  desc: '...', unit: 'ק״מ', step: 1000 }
```

No new endpoint, hook, or zod schema - the generic `/config/{key}` GET/PUT
already handles it. The MSW config handler gets the new key so the page test
stays green.

### Bot flow

New menu button **`🔢 עדכון ק״מ`** (callback `km_update`) added to **both**
`driver_menu()` and `admin_menu()` in `telegram-bot/app/keyboards.py`.

- **Driver**: resolve the driver's assigned vehicle (same fetch the `my_vehicle`
  flow uses), show current KM, prompt for the new value. State
  `{flow:"km_update", step:"awaiting_km", vehicle_id, current_km}`. No assigned
  vehicle -> friendly error.
- **Admin**: show a vehicle picker first (reuse the maintenance `pick_list`
  pattern, callback prefix `km_veh_`), then current KM + prompt. State carries
  `awaiting_vehicle` -> `awaiting_km`.
- **On input**: strip/normalize, `isdigit()` check, then `km >= current_km`
  check locally; `POST /km {vehicle_id, km, source:"telegram"}`. On `422`, map
  `detail` -> Hebrew message; on success -> confirmation. New strings in
  `texts.py`.

`source` is `"telegram"` for both roles (it denotes the channel, not the role).

Router wiring (`router.py`) maps callback `km_update` and the `km_update` flow
steps, mirroring the existing `maint_log` routing.

## Components / data flow

```
driver/admin taps "עדכון ק״מ"
  -> bot resolves vehicle (driver: own; admin: pick from /vehicles)
  -> bot shows current_km, prompts
  -> user types value
  -> bot: numeric + floor check (local)
  -> POST /km {vehicle_id, km, source:"telegram"}
       -> fleet-api: floor + cap check (422 on failure)
       -> repo.update_km: insert KmUpdate, set vehicle.current_km,
          maybe emit maintenance_due event
  -> bot: success confirmation, or mapped 422 message
```

## Error handling

| Condition | Where | Result |
|-----------|-------|--------|
| Non-numeric input | bot | re-prompt, invalid message |
| `km < current_km` | bot (local) + api (`422 km_below_current`) | "below current" message |
| `km - current_km > threshold` | api (`422 km_increment_too_large`) | "unreasonable" message |
| First reading (`current_km is None`) | - | accepted, no checks |
| Driver has no assigned vehicle | bot | friendly error, abort flow |

## Testing

- **fleet-api**: `/km` floor rejection, cap rejection, first-reading accepted,
  custom threshold honored via config, threshold company isolation.
- **telegram-bot**: e2e driver success + below-current; admin pick-vehicle +
  success; no-vehicle case; assert posted body `source == "telegram"`.
- **webui**: MSW config handler updated; existing config page test covers the
  new field.

## Docs / config impact

- No new env vars (`km_max_increment` is per-company SystemConfig, app-default
  10000) -> no `.env.example` change.
- Update this design's companion implementation doc and tick items as built.
- No schema migration: SystemConfig stores the key as JSONB by `(company_id,
  config_key)`; `KmUpdate` already exists.
