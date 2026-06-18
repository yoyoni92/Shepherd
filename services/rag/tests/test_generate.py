"""T6 - Retrieval prompt (surface #3).

>=10 fixture queries; answers must cite source plate and never fabricate.
Mock LLM returns an answer that includes the plate from the context -
simulating correct retrieval-grounded generation.
"""
import re
import uuid

import pytest

from app.generate import answer
from app.retrieve import query

PLATE_A = "111-11-111"
PLATE_B = "222-22-222"
BOGUS_PLATE = "999-99-999"

FIXTURE_QUERIES = [
    # (question, caller_context, expect_citations, expect_no_record, force_empty_retrieval)
    ("What is the status of plate 111-11-111?", {"role": "admin"}, True, False, False),
    ("Tell me about vehicle 222-22-222", {"role": "admin"}, True, False, False),
    ("מה הסטטוס של רכב 111-11-111?", {"role": "admin"}, True, False, False),
    ("ספר לי על הרכב 222-22-222", {"role": "admin"}, True, False, False),
    ("Is the insurance of 111-11-111 valid?", {"role": "admin"}, True, False, False),
    ("מתי הטיפול האחרון של 111-11-111?", {"role": "admin"}, True, False, False),
    ("What are the open tickets for 222-22-222?", {"role": "admin"}, True, False, False),
    ("When is 222-22-222 license expiring?", {"role": "admin"}, True, False, False),
    ("האם יש תאונות לרכב 111-11-111?", {"role": "admin"}, True, False, False),
    ("accident history for 222-22-222", {"role": "admin"}, True, False, False),
    # unknown plate: retrieval returns best-match docs; LLM (in prod) reasons no match.
    # Test only verifies no hallucinated bogus plate appears in citations.
    (f"What is the status of plate {BOGUS_PLATE}?", {"role": "admin"}, False, False, False),
    # empty question: short-circuit before retrieval
    ("", {"role": "admin"}, False, True, True),
    # driver with no vehicles: ownership filter blocks all docs -> empty retrieval
    (f"status of {PLATE_A}", {"role": "driver", "vehicle_ids": []}, False, True, False),
]


def _mock_llm(prompt: str) -> str:
    # Extract the first plate from context and cite it in the answer
    match = re.search(r"Vehicle: (\S+)", prompt)
    if match:
        return f"Vehicle {match.group(1)} is in good standing per the fleet records."
    return "No record found."


@pytest.fixture(scope="module")
def populated_collection(ef):
    import chromadb
    client = chromadb.EphemeralClient()
    col = client.get_or_create_collection("t6_fixtures", embedding_function=ef)
    vid_a = str(uuid.uuid4())
    vid_b = str(uuid.uuid4())
    col.upsert(
        documents=[
            f"Vehicle: {PLATE_A}\nDriver: Alice Cohen\nInsurance valid to: 2026-06-01\n"
            f"License valid to: 2026-12-01\nOpen tickets: 1\nLast maintenance: 2025-01-01 (small)",
            f"Vehicle: {PLATE_B}\nDriver: Bob Levi\nInsurance valid to: 2026-03-15\n"
            f"License valid to: 2027-01-01\nOpen tickets: 0\nLast maintenance: 2025-03-01 (big)",
        ],
        metadatas=[
            {"vehicle_id": vid_a, "plate": PLATE_A, "driver_id": "da", "customer_id": ""},
            {"vehicle_id": vid_b, "plate": PLATE_B, "driver_id": "db", "customer_id": ""},
        ],
        ids=[vid_a, vid_b],
    )
    return col


@pytest.mark.parametrize("question,ctx,expect_citations,expect_no_record,force_empty", FIXTURE_QUERIES)
def test_fixture_query(question, ctx, expect_citations, expect_no_record, force_empty, populated_collection):
    if force_empty or not question:
        retrieved = []
    else:
        retrieved = query(populated_collection, question, ctx, top_k=3)

    result = answer(question, retrieved, _mock_llm)

    if expect_no_record:
        assert result["answer"] == "No record found."
        assert result["citations"] == []
    elif expect_citations:
        assert result["citations"], "should have citations for known plates"
        # no hallucinated plates - only plates from citations may appear in answer
        allowed = set(result["citations"])
        for plate in re.findall(r"\d{3}-\d{2}-\d{3}", result["answer"]):
            assert plate in allowed, f"hallucinated plate {plate} in answer"
    else:
        # unknown plate: citations must not include the bogus plate
        assert BOGUS_PLATE not in result["citations"]
