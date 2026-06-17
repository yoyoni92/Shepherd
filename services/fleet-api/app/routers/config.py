from fastapi import APIRouter, HTTPException, status

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import ConfigRead, ConfigUpdate

router = APIRouter(prefix="/config", tags=["config"])


def _to_read(c) -> ConfigRead:
    return ConfigRead(
        config_key=c.config_key,
        config_value=c.config_value,
        description=c.description,
    )


@router.get(
    "",
    response_model=list[ConfigRead],
    summary="List system config",
    description="Return all system configuration entries. Readable by any authenticated caller.",
)
def list_config(session: Db, caller: Caller) -> list[ConfigRead]:
    assert_permitted(caller.role, Action.READ_CONFIG)
    return [_to_read(c) for c in repo.get_all_config(session)]


@router.get(
    "/{key}",
    response_model=ConfigRead,
    summary="Get config by key",
)
def get_config(key: str, session: Db, caller: Caller) -> ConfigRead:
    assert_permitted(caller.role, Action.READ_CONFIG)
    entry = repo.get_config_key(session, key)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config key not found")
    return _to_read(entry)


@router.put(
    "/{key}",
    response_model=ConfigRead,
    summary="Update config (admin only)",
    description="Set or update a system configuration value.",
)
def update_config(key: str, body: ConfigUpdate, session: Db, caller: Caller) -> ConfigRead:
    assert_permitted(caller.role, Action.EDIT_CONFIG)
    return _to_read(repo.set_config(session, key, body.config_value))
