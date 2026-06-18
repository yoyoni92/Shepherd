import uuid
from unittest.mock import MagicMock

from tests.conftest import make_mock_vehicle
from app.sync import bulk, upsert


def _mock_session(vehicles, accident_map=None, ticket_map=None):
    """Build a mock Session that returns the given vehicles list and empty accidents/tickets."""
    session = MagicMock()
    call_count = [0]

    def scalars_side(stmt):
        call_count[0] += 1
        mock_result = MagicMock()
        if call_count[0] == 1:
            mock_result.__iter__ = lambda s: iter(vehicles)
            # also support list(session.scalars(...))
            mock_result.all.return_value = vehicles
        else:
            mock_result.all.return_value = []
        return mock_result

    session.scalars.side_effect = scalars_side
    session.scalar.return_value = 0  # open ticket count
    return session


# T3 - Index + metadata
def test_bulk_index_metadata(collection):
    vid1 = str(uuid.uuid4())
    vid2 = str(uuid.uuid4())
    v1 = make_mock_vehicle("111-11-111", vid=vid1)
    v2 = make_mock_vehicle("222-22-222", vid=vid2)

    session = _mock_session([v1, v2])
    count = bulk(session, collection)

    assert count == 2
    res = collection.get(include=["metadatas"])
    assert len(res["ids"]) == 2
    plates = {m["plate"] for m in res["metadatas"]}
    assert plates == {"111-11-111", "222-22-222"}
    # all required metadata keys present
    for m in res["metadatas"]:
        assert "vehicle_id" in m
        assert "driver_id" in m
        assert "customer_id" in m


# T5 - Incremental re-sync
def test_upsert_replaces_stale(collection):
    vid = str(uuid.uuid4())
    v = make_mock_vehicle("111-11-111", vid=vid)

    session = _mock_session([v])
    bulk(session, collection)

    # simulate data change - plate update
    v.licensing_plate = "111-11-999"
    session2 = MagicMock()
    session2.get.return_value = v
    session2.scalars.return_value.all.return_value = []
    session2.scalar.return_value = 0

    upsert(session2, collection, vid)

    res = collection.get(ids=[vid], include=["documents", "metadatas"])
    assert res["metadatas"][0]["plate"] == "111-11-999"
    assert "111-11-999" in res["documents"][0]
    assert "111-11-111" not in res["documents"][0]


def test_upsert_missing_vehicle_deletes(collection):
    vid = str(uuid.uuid4())
    v = make_mock_vehicle("333-33-333", vid=vid)

    session = _mock_session([v])
    bulk(session, collection)

    session2 = MagicMock()
    session2.get.return_value = None  # vehicle deleted
    upsert(session2, collection, vid)

    res = collection.get(ids=[vid])
    assert res["ids"] == []
