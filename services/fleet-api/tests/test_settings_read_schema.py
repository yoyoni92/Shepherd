from types import SimpleNamespace
from uuid import uuid4

from app.routers.companies import _settings_read


def test_settings_read_exposes_schema_name():
    s = SimpleNamespace(
        gdrive_folder_id=None,
        gdrive_credentials_json=None,
        feature_flags={},
        schema_name="co_acme",
    )
    out = _settings_read(uuid4(), s)
    assert out.schema_name == "co_acme"
