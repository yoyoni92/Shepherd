import uuid

from app.retrieve import query, _build_where


# T4 - Ownership filter is a HARD filter
def test_driver_sees_only_own_vehicle(collection):
    vid_a = str(uuid.uuid4())
    vid_b = str(uuid.uuid4())

    collection.upsert(
        documents=[
            "Vehicle: 111-11-111\nDriver: Alice\nInsurance valid to: 2026-01-01",
            "Vehicle: 222-22-222\nDriver: Bob\nInsurance valid to: 2026-01-01",
        ],
        metadatas=[
            {"vehicle_id": vid_a, "plate": "111-11-111", "driver_id": "da", "customer_id": ""},
            {"vehicle_id": vid_b, "plate": "222-22-222", "driver_id": "db", "customer_id": ""},
        ],
        ids=[vid_a, vid_b],
    )

    # Query semantically closer to vid_b ("222") but as driver who owns vid_a
    results = query(
        collection,
        question="222-22-222 vehicle status",
        caller_context={"role": "driver", "vehicle_ids": [vid_a]},
        top_k=3,
    )
    returned_ids = {r["metadata"]["vehicle_id"] for r in results}
    assert vid_b not in returned_ids, "ownership filter must block vid_b"
    assert vid_a in returned_ids


def test_admin_sees_all(collection):
    vid_a = str(uuid.uuid4())
    vid_b = str(uuid.uuid4())

    collection.upsert(
        documents=[
            "Vehicle: 111-11-111\nDriver: Alice",
            "Vehicle: 222-22-222\nDriver: Bob",
        ],
        metadatas=[
            {"vehicle_id": vid_a, "plate": "111-11-111", "driver_id": "", "customer_id": ""},
            {"vehicle_id": vid_b, "plate": "222-22-222", "driver_id": "", "customer_id": ""},
        ],
        ids=[vid_a, vid_b],
    )
    results = query(collection, "vehicle", {"role": "admin"}, top_k=5)
    ids = {r["metadata"]["vehicle_id"] for r in results}
    assert vid_a in ids
    assert vid_b in ids


def test_build_where_admin():
    assert _build_where({"role": "admin"}) is None


def test_build_where_driver_single():
    w = _build_where({"role": "driver", "vehicle_ids": ["v1"]})
    assert w == {"vehicle_id": {"$eq": "v1"}}


def test_build_where_driver_multi():
    w = _build_where({"role": "driver", "vehicle_ids": ["v1", "v2"]})
    assert w == {"vehicle_id": {"$in": ["v1", "v2"]}}


def test_build_where_driver_no_vehicles():
    w = _build_where({"role": "driver", "vehicle_ids": []})
    assert w == {"vehicle_id": {"$eq": "__none__"}}
