# telegram-bot - known bugs

## BUG-1: vehicle_issue posts invalid Fleet event enums -> POST /events 500, no row written

- **Status:** FIXED (2026-06-26)
- **Severity:** high - a driver-reported fault is silently dropped
- **Component:** `services/telegram-bot/app/flows/vehicle_issue.py`
- **Found:** 2026-06-26, via the cross-system integration suite (`tests/e2e/`)

### Summary

When a driver reports a vehicle issue, the bot builds the event payload with
`event_type="warning"` and `source_type="telegram"`. Neither is a valid value in Fleet
API's enums, so `POST /events` fails. The bot does **not** check the response - it clears
the session, replies `✅ התקלה נרשמה.` and sends the dice flourish regardless - so the
driver is told the fault was logged while **no `events` row is ever created**.

This was faithfully ported from the original n8n workflow
(`plans/shepherd-telegram-bot.monolith.json`: `event_type:'warning'`,
`source_type:'telegram'`), which wrote without enforcing the current enum.

### Reproduce

Against the live stack (`make up`), with the real internal token:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/events \
  -H "X-Internal-Token: $INTERNAL_SERVICE_TOKEN" \
  -H 'X-Caller-Context: {"role":"admin"}' \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id":null,"event_type":"warning","severity":"warning",
       "message":"t","source_type":"telegram"}'
# -> 500     (a valid event_type such as "maintenance_due" -> 201)
```

Or drive the flow: enroll a driver, tap "דיווח תקלה", send any text. The bot replies
success but `SELECT * FROM events WHERE vehicle_id = <driver's vehicle>` returns nothing.

### Root cause

- Fleet `events.event_type` is the `event_type_enum`: `maintenance_due`,
  `license_expiring`, `insurance_expiring`, `ticket_received`, `accident_logged`
  (`db/shepherd_db/models.py`). `"warning"` is not a member.
- Fleet `events.source_type` is the `event_source_type_enum`: `km_updates`, `scheduler`,
  `accidents`, `reports`. `"telegram"` is not a member.
- `severity="warning"` is valid (`info|warning|critical`) - only the two fields above are wrong.
- The flow never inspects the Fleet response, so the failure is invisible to the driver.

### Impact

Driver fault reports never reach the fleet. Admins never see them; nothing is persisted.

### Fix (applied - option 1)

- Added `vehicle_issue` to `event_type_enum` and `telegram` to `event_source_type_enum`
  in `db/shepherd_db/models.py` (models are the schema source). Applied to the live DB
  with `ALTER TYPE ... ADD VALUE` (no wipe); fresh builds get them from `create_all`.
- `app/flows/vehicle_issue.py` now posts `event_type="vehicle_issue"` /
  `source_type="telegram"` and **checks the response**: on non-2xx it sends
  `texts.VEHICLE_ISSUE_FAILED` instead of falsely reporting success + dice.
- Rebuilt fleet-api + telegram-bot. Verified: `POST /events` with the new pair -> 201.

### Test

`test_vehicle_issue_writes_event_row` re-added to `tests/e2e/test_integration.py`
(asserts one `events` row with `event_type='vehicle_issue'`, `source_type='telegram'`,
and the driver's message). Passes against the live stack.
