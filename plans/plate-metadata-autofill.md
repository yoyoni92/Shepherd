# License-plate metadata auto-fill: "type a plate, fields fill themselves"

When an admin adds a vehicle, blurring the license-plate field looks the plate up
against Israel's public Ministry of Transport registry (data.gov.il) and
auto-fills manufacturer, model, year, fuel, color, VIN and license expiry. The
admin reviews and can override before saving. This is the build plan.

## Source of truth (external)

- **API:** data.gov.il CKAN datastore, `datastore_search`. Public, keyless, free.
  - Endpoint: `https://data.gov.il/api/3/action/datastore_search`
  - Resource (private + commercial vehicles): `053cea08-09bc-40ec-8f7a-156f0677aff3`
  - Query: `filters={"mispar_rechev": <plate-as-int>}` (exact match; do **not**
    use free-text `q`, it over-matches). Plate must be an integer - strip dashes/spaces.
- Verified live: plate `1000028` returns make `פורשה גרמניה`, trade name
  `MACAN S DIESEL`, year `2016`, fuel `דיזל`, VIN `WP1ZZZ95ZGLB70121`, `tokef_dt 2027-03-15`.
- Public registry only - **no owner/personal data** is returned.

## Field mapping (gov record → Shepherd `Vehicle`)

| gov field | meaning | Shepherd field | notes |
|---|---|---|---|
| `tozeret_nm` | manufacturer | `vendor` | raw string (may include country, e.g. "פורשה גרמניה") |
| `kinuy_mishari` | trade name | `model` | fall back to `degem_nm` if empty |
| `shnat_yitzur` | model year | `year` | **new column** |
| `sug_delek_nm` | fuel | `fuel_type` | **new column**, Hebrew string ("דיזל") |
| `tzeva_rechev` | color | `color` | **new column** |
| `misgeret` | VIN / chassis | `vin` | **new column** |
| `tokef_dt` | license valid-to | `license_valid_to` | parse `YYYY-MM-DD` |
| `sug_degem` = `P` | private car | `vehicle_type` | **not** auto-set (see below) |

## Decisions (locked)

- **Where it runs:** fleet-api owns the lookup + Hebrew→model mapping, exposed as a
  read-only endpoint the webui calls. Mirrors the existing "match-by-plate → fill
  vehicle" precedent in `routers/documents.py` (`POST /documents/extracted`).
- **Suggest-only:** the endpoint never persists. Creation still goes through the
  unchanged `POST /vehicles`. The lookup only returns suggested field values.
- **Trigger:** auto-fetch on **plate-field blur** in the add-vehicle form (create
  mode only, not edit). Fires only when the plate passes `plateGuard` and differs
  from the last plate looked up (debounce/guard against repeat fetches).
- **Non-destructive fill:** only populate suggested fields that are currently
  **empty** - never clobber something the admin already typed.
- **New columns:** `year` (Integer), `fuel_type` (Text), `color` (Text), `vin`
  (Text) on `Vehicle`, all nullable. DB is wiped & rebuilt from models (no
  migrations) - add columns to `models.py` and rebuild.
- **`vehicle_type` stays manual:** the private+commercial resource can't reliably
  distinguish car/van/truck/bus; leave it a required manual select (may default "car").
- **Config, not secret:** data.gov.il is public + keyless. Base URL goes in
  `[services]` config (overridable); resource ID is a module constant. No new `.env` secret.
- **Non-blocking:** any failure (timeout, not-found, gov API down) returns
  `found=false` gracefully; vehicle creation never depends on the lookup. Short
  client timeout (~8s).
- **Scope v1:** private + commercial resource only. Motorcycle / heavy-vehicle
  fallback resources deferred to v2.

## Tasks

### 1. DB model (`db/shepherd_db/models.py`)
- Add to `Vehicle`: `year` (Integer, nullable), `fuel_type` (Text, nullable),
  `color` (Text, nullable), `vin` (Text, nullable).
- Rebuild schema (`db/create_schema.py`) - no migration.

### 2. fleet-api plate-lookup client (`services/fleet-api/app/plate_lookup.py` - new)
- Modeled on `app/vision.py` (lazy client, tolerant parse, `(ok, data)` return),
  using the already-present `httpx`.
- `normalize_plate("12-345-67") -> 1234567` (strip non-digits; reject empty).
- `RESOURCE_ID` constant; base URL from `get_config().services.gov_vehicle_api_url`.
- `lookup(plate) -> PlateLookupResult`: call `datastore_search` with the exact
  `filters`, ~8s timeout; map first record via the table above; parse `tokef_dt`
  to a date. All exceptions/empty results → `found=false`. Never raises.

### 3. fleet-api schema + endpoint
- `schemas.py`: add `year`, `fuel_type`, `color`, `vin` to `VehicleCreate`,
  `VehicleUpdate`, `VehicleRead`. New `PlateLookupResult` (found flag + suggested fields).
- `routers/vehicles.py`: `GET /vehicles/plate-lookup?plate=...` guarded by
  `MANAGE_VEHICLES` (same admin gate as create) → calls `plate_lookup.lookup`.
- `repo.py`: `create_vehicle`/`update_vehicle` already do `Vehicle(**data)` /
  attribute set - new fields flow through once they're on the schema. Confirm the
  read path returns them.

### 4. Config (`libs/shepherd_config` + TOMLs)
- Add `gov_vehicle_api_url` to `ServicesConfig` (loader.py), default
  `https://data.gov.il/api/3/action/datastore_search`.
- Add `gov_vehicle_api_url` under `[services]` in `config.toml` and
  `config.example.toml`.

### 5. webui
- `lib/api/schemas.ts`: add `year`/`fuel_type`/`color`/`vin` to `VehicleCreate`,
  `VehicleRead`, `UiVehicle`; new `PlateLookupSchema`. `lib/adapters.ts`:
  `toUiVehicle` carries the new fields.
- `lib/api/fleet.ts`: `lookupPlate(plate) -> GET /vehicles/plate-lookup` via the
  existing `/api/fleet` proxy + `get` helper.
- `components/EntityFormModal.tsx`: add optional `FieldDef.onBlur?: (value, values)
  => Promise<Partial<values> | null>`. On blur, run it and **merge only into empty
  fields**; show a small inline spinner + "מולא מנתוני משרד התחבורה" hint and a
  subtle "לא נמצא" note when `found=false`. (This is the one structural change -
  the modal currently has no way to push values in after mount.)
- `vehicles/page.tsx`: wire `onBlur` on `licensing_plate` (create mode only) to
  `lookupPlate`; add `year`/`fuel_type`/`color`/`vin` to `formFields`.

### 6. telegram-bot
- No change. The bot has no add-vehicle flow (all vehicle interactions are reads
  or field patches). New read fields surface automatically via `GET /vehicles`.

### 7. Docs (pre-commit rule)
- This plan, the "Mirrors fleet-api" comment in `lib/api/schemas.ts`,
  `config.example.toml`, READMEs if setup/commands change. No new `.env` secret.

## Tests
- **fleet-api** (`test_plate_lookup.py`): `normalize_plate` cases; `map_record`
  against a captured fixture of the verified Porsche record; graceful `found=false`
  on mocked httpx timeout/error and on empty `records`.
- **fleet-api** endpoint: `GET /vehicles/plate-lookup` auth gate + happy/not-found
  (gov call mocked - no live network in tests).
- **webui**: `EntityFormModal` blur merges only empty fields; msw handler for
  `plate-lookup`; adapter carries new fields.

## Definition of done
- Blurring a valid plate in the add-vehicle form fills empty `vendor`, `model`,
  `year`, `fuel_type`, `color`, `vin`, `license_valid_to`, leaving already-typed
  values untouched; admin can edit any of them before saving.
- Unknown/absent plate shows a subtle "not found" note and leaves the form fully
  editable; gov API being slow/down never blocks or errors the create flow.
- `year`/`fuel_type`/`color`/`vin` persist on create and round-trip through
  `GET /vehicles` and the webui vehicle views.
- Lookup is admin-gated (`MANAGE_VEHICLES`) and makes no live network calls in tests.
- All suites green; docs updated in the same commit.
