from uuid import UUID

from fastapi import APIRouter

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import EventCreate, EventRead

router = APIRouter(prefix="/events", tags=["events"])


def _to_read(e) -> EventRead:
    return EventRead(
        event_id=e.event_id,
        vehicle_id=e.vehicle_id,
        event_type=e.event_type.value,
        severity=e.severity.value,
        message=e.message,
        status=e.status.value,
        triggered_ts=e.triggered_ts,
    )


@router.get(
    "",
    response_model=list[EventRead],
    summary="List events (admin only)",
    description="Return system events, optionally filtered by vehicle.",
)
def list_events(session: Db, caller: Caller, vehicle_id: UUID | None = None) -> list[EventRead]:
    assert_permitted(caller.role, Action.READ_EVENTS)
    return [_to_read(e) for e in repo.list_events(session, vehicle_id=vehicle_id)]


@router.post(
    "",
    response_model=EventRead,
    status_code=201,
    summary="Create event (admin/system only)",
    description="Emit a system event.",
)
def create_event(body: EventCreate, session: Db, caller: Caller) -> EventRead:
    assert_permitted(caller.role, Action.WRITE_EVENTS)
    data = body.model_dump()
    event = repo.create_event(session, data)
    return _to_read(event)
