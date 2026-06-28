# mypy typecheck setup - report

## Per-package mypy result

| Package | Command | Result |
|---|---|---|
| `libs` (shepherd_contracts) | `cd libs && poetry run mypy .` | Success: no issues found in 3 source files |
| `libs/shepherd_config` | `cd libs/shepherd_config && poetry run mypy .` | Success: no issues found in 4 source files |
| `db` (shepherd_db) | `cd db && poetry run mypy .` | Success: no issues found in 20 source files |
| `services/fleet-api` | `cd services/fleet-api && poetry run mypy .` | Success: no issues found in 57 source files |
| `services/telegram-bot` | `cd services/telegram-bot && poetry run mypy .` | Success: no issues found in 37 source files |

## Changes made

### Step 1: py.typed markers
Created empty `py.typed` marker files in:
- `libs/shepherd_contracts/py.typed`
- `db/shepherd_db/py.typed`
- `libs/shepherd_config/shepherd_config/py.typed`

### Step 2: mypy dev-dep + [tool.mypy] config
Added `mypy = "^1.11"` to dev-deps and `[tool.mypy]` section to all 5 `pyproject.toml` files.
- `libs/pyproject.toml` - includes `exclude = "shepherd_config/"` to prevent recursion into nested package
- `libs/shepherd_config/pyproject.toml`
- `db/pyproject.toml`
- `services/fleet-api/pyproject.toml`
- `services/telegram-bot/pyproject.toml`

All configs use `python_version = "3.12"` and `ignore_missing_imports = true`.

### Step 3: Real type errors fixed

**db/tests/conftest.py** (1 error)
- `os.unlink` in lambda `and` chain - changed to ternary `if os.path.exists(...) else None`

**services/fleet-api** (6 errors)
- `app/repo.py`: added `assert vehicle is not None` in `update_km` and `create_care` to narrow `Vehicle | None`
- `app/repo.py`: added `assert isinstance(session.bind, SAConnection)` in `find_enrollment_by_phone` where comment explicitly states session.bind is a Connection
- `app/repo.py`: added `# type: ignore[attr-defined]` for `care._next_km/date/type` - runtime-only ORM instance attrs not in model definition
- `app/routers/auth.py`: added type annotation `feature_flags: dict[str, object] = {}`
- `app/routers/care.py`: added `# type: ignore[attr-defined]` for reading `care._next_km/date/type`
- `tests/conftest.py`: same `os.unlink` ternary fix

**services/telegram-bot** (39 errors - all fixed)

Patterns and fixes:
1. `FleetClient.driver_vehicle(driver_id: str)` changed to accept `str | None` (early return None) - fixed 4 callers (accident/km_update/my_vehicle/vehicle_issue)
2. `validate.field_from_callback/value_prompt/validate` changed to accept `str | None` params - fixed 8 callers
3. `CallbackQuery.message` is `Message | InaccessibleMessage | None` in aiogram - added `assert isinstance(c.message, Message)` in `normalize_callback`
4. `FLOW_TO_FEATURE[ctx.flow]` where `ctx.flow: str | None` - added `assert ctx.flow is not None` (active_route guarantees flow is set when it returns non-None)
5. `ctx.whoami.get(...)` where `ctx.whoami: dict | None` - changed to `(ctx.whoami or {}).get(...)` in sysadmin.py private functions
6. `ctx.callback_data` used without None check - added `assert ctx.callback_data is not None` in 7 route branches
7. `ctx.photo_id/video_id` passed to `download()` - added asserts in `_store_photo` and `accident_area_video`
8. `doc_scan.py` `file_id = photo_id or document_id` - added assert before download
9. `access.py` `enroll(ctx.contact_phone)` - added `if not ctx.contact_phone: return` guard
10. `update_driver/update_details` `_INVALID.get(field, ...)` where field is `Any | None` - used `field_key: str | None` variable and `field_key or ""` as dict key

## Test suite counts

| Package | Tests |
|---|---|
| `libs` | 4 passed |
| `libs/shepherd_config` | 5 passed |
| `db` | 38 passed |
| `services/fleet-api` | 178 passed |
| `services/telegram-bot` | 73 passed |

All test counts match expected values. No regressions.

## Ruff status

`uvx ruff check .` - All checks passed.
