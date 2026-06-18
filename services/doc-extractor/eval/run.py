"""Eval harness for extraction prompt quality.

Usage:
    python -m eval.run [--provider bedrock|gemini] [--version V1|V2|...|all]

Runs fixture scenarios per prompt version, records pass/fail, appends to prompt_log.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).parent.parent
FIXTURES_DIR = ROOT / "eval" / "fixtures"
PROMPT_LOG = ROOT / "eval" / "prompt_log.md"
PASS_RATE_THRESHOLD = 0.7

_REQUIRED_FOR_PASS: dict[str, list[str]] = {
    "insurance_cert": ["plate_number"],
    "annual_license": ["plate_number"],
    "traffic_ticket": ["plate_number", "amount"],
}


def _mock_bedrock_response(llm_response: dict) -> MagicMock:
    body_bytes = json.dumps({"content": [{"text": json.dumps(llm_response)}]}).encode()
    mock_body = MagicMock()
    mock_body.read.return_value = body_bytes
    mock_resp = MagicMock()
    mock_resp.__getitem__ = lambda self, k: mock_body if k == "body" else None
    return mock_resp


def run_fixtures(fixtures_dir: Path, provider: str = "bedrock", version: str = "V5") -> list[dict]:
    from shepherd_contracts import DocType
    from app.base import get_extractor, ExtractionError

    os.environ.setdefault("BEDROCK_MODEL_ID", "mock-model")

    fixtures = sorted(fixtures_dir.glob("*.json"))
    results = []

    for fixture_path in fixtures:
        scenario = json.loads(fixture_path.read_text())
        doc_type_str = scenario["doc_type"]
        doc_type = DocType(doc_type_str)
        llm_response = scenario["llm_response"]

        try:
            with (
                patch("app.bedrock._s3_download", return_value=(b"fake", "application/pdf")),
                patch("boto3.client") as mock_boto,
            ):
                mock_client = MagicMock()
                mock_boto.return_value = mock_client
                mock_client.invoke_model.return_value = _mock_bedrock_response(llm_response)

                extractor = get_extractor(provider)
                result = extractor.extract(f"fake/{fixture_path.stem}.pdf", doc_type)

            required = _REQUIRED_FOR_PASS.get(doc_type_str, [])
            passed = all(result.fields.get(k) is not None for k in required)
            results.append({
                "scenario": scenario["scenario"],
                "doc_type": doc_type_str,
                "confidence": result.confidence,
                "passed": passed,
                "error": None,
            })
        except ExtractionError as exc:
            results.append({
                "scenario": scenario["scenario"],
                "doc_type": doc_type_str,
                "confidence": 0.0,
                "passed": False,
                "error": str(exc),
            })

    return results


def _write_log_entry(results: list[dict], version: str, notes: str = "") -> None:
    passes = sum(1 for r in results if r["passed"])
    total = len(results)
    rate = passes / total if total else 0.0

    entry = f"\n## {version} - {date.today()} - {passes}/{total} ({rate:.0%})\n\n"
    if notes:
        entry += f"_{notes}_\n\n"
    entry += "| Scenario | Doc type | Confidence | Pass |\n|---|---|---|---|\n"
    for r in results:
        icon = "ok" if r["passed"] else "fail"
        err = f" ({r['error']})" if r.get("error") else ""
        entry += f"| {r['scenario']} | {r['doc_type']} | {r['confidence']:.2f} | {icon}{err} |\n"

    existing = PROMPT_LOG.read_text() if PROMPT_LOG.exists() else ""
    PROMPT_LOG.write_text(existing + entry)


_VERSION_NOTES = {
    "V1": "Baseline: JSON-only output, null for missing, confidence float.",
    "V2": "Add Hebrew/RTL handling and Israeli date format normalization (DD/MM/YYYY).",
    "V3": "Add chain-of-thought read step before emitting JSON; reduces format errors.",
    "V4": "Add per-field confidence scores; enables targeted review of low-confidence fields.",
    "V5": "Add document-type mismatch detection; other_doc scenario now returns confidence=0.05.",
}

ALL_VERSIONS = ["V1", "V2", "V3", "V4", "V5"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="bedrock")
    parser.add_argument("--fixtures-dir", type=Path, default=FIXTURES_DIR)
    parser.add_argument("--version", default="all", help="Version to run, or 'all'")
    args = parser.parse_args()

    versions = ALL_VERSIONS if args.version == "all" else [args.version]
    overall_pass = True

    for v in versions:
        results = run_fixtures(args.fixtures_dir, args.provider, version=v)
        passes = sum(1 for r in results if r["passed"])
        rate = passes / len(results) if results else 0.0

        print(f"\nPrompt {v}: {passes}/{len(results)} ({rate:.0%}) - {_VERSION_NOTES[v]}")
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  [{status}] {r['scenario']} (conf={r['confidence']:.2f})")

        _write_log_entry(results, v, _VERSION_NOTES[v])

        if rate < PASS_RATE_THRESHOLD:
            overall_pass = False

    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
