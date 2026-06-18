"""Eval harness for RAG surface #3 - run and append pass-rates to prompt_log.md.

Usage:
    poetry run python -m eval.run [--version V6] [--live]

Without --live, uses a mock LLM (deterministic, always cites the plate).
With --live, requires LLAMA_MODEL_PATH to be set.
"""
import argparse
import re
import sys
import uuid
from datetime import date
from pathlib import Path

import chromadb

from app.embed import get_chroma_ef
from app.generate import answer
from app.retrieve import query

LOG_PATH = Path(__file__).parent / "prompt_log.md"

PLATE_A = "111-11-111"
PLATE_B = "222-22-222"

FIXTURES = [
    ("What is the status of plate 111-11-111?", {"role": "admin"}, lambda r: PLATE_A in r["citations"]),
    ("Tell me about vehicle 222-22-222", {"role": "admin"}, lambda r: PLATE_B in r["citations"]),
    ("מה הסטטוס של רכב 111-11-111?", {"role": "admin"}, lambda r: PLATE_A in r["citations"]),
    ("ספר לי על הרכב 222-22-222", {"role": "admin"}, lambda r: PLATE_B in r["citations"]),
    ("Is the insurance of 111-11-111 valid?", {"role": "admin"}, lambda r: PLATE_A in r["citations"]),
    ("מתי הטיפול האחרון של 111-11-111?", {"role": "admin"}, lambda r: PLATE_A in r["citations"]),
    ("What are the open tickets for 222-22-222?", {"role": "admin"}, lambda r: PLATE_B in r["citations"]),
    ("When is 222-22-222 license expiring?", {"role": "admin"}, lambda r: PLATE_B in r["citations"]),
    ("האם יש תאונות לרכב 111-11-111?", {"role": "admin"}, lambda r: PLATE_A in r["citations"]),
    ("accident history for 222-22-222", {"role": "admin"}, lambda r: PLATE_B in r["citations"]),
    ("What is the status of plate 999-99-999?", {"role": "admin"}, lambda r: r["answer"] == "No record found."),
    ("", {"role": "admin"}, lambda r: r["answer"] == "No record found."),
]


def _build_collection():
    client = chromadb.EphemeralClient()
    col = client.get_or_create_collection("eval", embedding_function=get_chroma_ef())
    col.upsert(
        documents=[
            f"Vehicle: {PLATE_A}\nDriver: Alice Cohen\nInsurance valid to: 2026-06-01\n"
            f"License valid to: 2026-12-01\nOpen tickets: 1\nLast maintenance: 2025-01-01 (small)",
            f"Vehicle: {PLATE_B}\nDriver: Bob Levi\nInsurance valid to: 2026-03-15\n"
            f"License valid to: 2027-01-01\nOpen tickets: 0\nLast maintenance: 2025-03-01 (big)",
        ],
        metadatas=[
            {"vehicle_id": str(uuid.uuid4()), "plate": PLATE_A, "driver_id": "", "customer_id": ""},
            {"vehicle_id": str(uuid.uuid4()), "plate": PLATE_B, "driver_id": "", "customer_id": ""},
        ],
        ids=[str(uuid.uuid4()), str(uuid.uuid4())],
    )
    return col


def _mock_llm(prompt: str) -> str:
    match = re.search(r"Vehicle: (\S+)", prompt)
    return f"Vehicle {match.group(1)} is in good standing." if match else "No record found."


def run_eval(llm, version: str) -> list[dict]:
    col = _build_collection()
    rows = []
    for question, ctx, check in FIXTURES:
        if not question:
            result = answer(question, [], llm)
        else:
            retrieved = query(col, question, ctx, top_k=3)
            result = answer(question, retrieved, llm)
        passed = check(result)
        rows.append({"scenario": question[:40] or "(empty)", "pass": passed, "citations": result["citations"]})
    return rows


def append_log(version: str, rows: list[dict]) -> None:
    passed = sum(1 for r in rows if r["pass"])
    total = len(rows)
    today = date.today().isoformat()
    block = f"\n## {version} - {today} - {passed}/{total} ({100*passed//total}%)\n\n"
    block += "| Scenario | Citations | Pass |\n|---|---|---|\n"
    for r in rows:
        status = "ok" if r["pass"] else "fail"
        cites = ", ".join(r["citations"]) or "-"
        block += f"| {r['scenario']} | {cites} | {status} |\n"
    with open(LOG_PATH, "a") as f:
        f.write(block)
    print(f"{version}: {passed}/{total} ({100*passed//total}%) - appended to {LOG_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="V6")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    if args.live:
        import os
        from langchain_community.llms import LlamaCpp
        llm_obj = LlamaCpp(model_path=os.environ["LLAMA_MODEL_PATH"], temperature=0, max_tokens=512, verbose=False)
        llm = llm_obj.invoke
    else:
        llm = _mock_llm

    rows = run_eval(llm, args.version)
    append_log(args.version, rows)
    passed = sum(1 for r in rows if r["pass"])
    sys.exit(0 if passed == len(rows) else 1)
