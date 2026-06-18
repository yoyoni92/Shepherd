import uuid

import chromadb
import pytest

from app.embed import get_chroma_ef


@pytest.fixture(scope="session")
def ef():
    return get_chroma_ef()


@pytest.fixture
def collection(ef):
    client = chromadb.EphemeralClient()
    col = client.get_or_create_collection(f"test_{uuid.uuid4().hex[:8]}", embedding_function=ef)
    yield col


def make_mock_vehicle(plate: str, vid: str | None = None, driver=None, customer=None):
    from unittest.mock import MagicMock
    v = MagicMock()
    v.vehicle_id = vid or str(uuid.uuid4())
    v.licensing_plate = plate
    v.driver = driver
    v.driver_id = driver.driver_id if driver else None
    v.customer = customer
    v.customer_id = customer.customer_id if customer else None
    v.insurance_valid_to = None
    v.license_valid_to = None
    v.last_maintenance_date = None
    v.last_maintenance_type = None
    v.next_maintenance_km = None
    v.current_km = None
    return v
