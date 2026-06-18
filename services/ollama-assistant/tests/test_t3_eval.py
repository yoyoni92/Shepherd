"""T3 - Eval harness: cases.yaml has >=10 cases; all 5 prompt versions exist."""
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CASES_FILE = REPO_ROOT / "eval" / "ollama" / "cases.yaml"
PROMPTS_DIR = REPO_ROOT / "prompts"


def test_eval_cases_has_at_least_10():
    cases = yaml.safe_load(CASES_FILE.read_text())["cases"]
    assert len(cases) >= 10, f"Need >=10 eval cases, got {len(cases)}"


def test_five_prompt_versions_exist():
    versions = list(PROMPTS_DIR.glob("ollama_system_v*.txt"))
    assert len(versions) >= 5, f"Need 5 prompt versions, found {len(versions)}"


def test_eval_runner_importable():
    import importlib.util
    runner = REPO_ROOT / "eval" / "ollama" / "run.py"
    spec = importlib.util.spec_from_file_location("run", runner)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.run_version)
    assert callable(mod.main)
