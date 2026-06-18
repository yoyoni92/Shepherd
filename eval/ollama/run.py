#!/usr/bin/env python3
"""Eval harness: run >=10 cases against V1..V5 system prompts and report pass rate.

Usage:
    OLLAMA_URL=http://localhost:11434 python eval/ollama/run.py
"""
import os
import sys
from pathlib import Path

import httpx
import yaml

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
CASES_FILE = Path(__file__).parent / "cases.yaml"
TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "60"))


def _chat(system_prompt: str, user_text: str) -> str:
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "stream": False,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _passes(case: dict, response: str) -> bool:
    check = case["check"]
    resp_lower = response.lower()
    if check == "contains_any":
        return any(kw.lower() in resp_lower for kw in case["keywords"])
    if check == "refusal":
        return case["refusal_phrase"].lower() in resp_lower
    return False


def run_version(version: str, cases: list, system_prompt: str) -> float:
    passed = 0
    for case in cases:
        try:
            response = _chat(system_prompt, case["input"])
            ok = _passes(case, response)
        except Exception as e:
            print(f"  [{case['id']}] ERROR: {e}")
            ok = False
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {case['id']}")
        if ok:
            passed += 1
    rate = passed / len(cases) * 100
    print(f"  {version}: {passed}/{len(cases)} = {rate:.0f}%\n")
    return rate


def main():
    cases = yaml.safe_load(CASES_FILE.read_text())["cases"]
    versions = sorted(PROMPTS_DIR.glob("ollama_system_v*.txt"))
    if not versions:
        print("No prompt versions found in", PROMPTS_DIR)
        sys.exit(1)

    results = {}
    for path in versions:
        v = path.stem.replace("ollama_system_", "")
        print(f"=== {v} ({path.name}) ===")
        results[v] = run_version(v, cases, path.read_text())

    best = max(results, key=results.get)
    print(f"Best version: {best} ({results[best]:.0f}%)")


if __name__ == "__main__":
    main()
