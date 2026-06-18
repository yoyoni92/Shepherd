"""T4 - Live smoke test (gated: requires local Ollama + llama3 model)."""
import os
import pytest
import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
SYSTEM_PROMPT_PATH = os.environ.get(
    "SYSTEM_PROMPT_PATH",
    str(__import__("pathlib").Path(__file__).parent.parent.parent.parent / "prompts" / "ollama_system.txt"),
)


def _ollama_ready() -> bool:
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        resp.raise_for_status()
        model = os.environ.get("OLLAMA_MODEL", "llama3")
        models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
        return model in models
    except Exception:
        return False


pytestmark = pytest.mark.live


@pytest.fixture(autouse=True)
def require_ollama():
    if not _ollama_ready():
        pytest.skip(f"Ollama not running or model not pulled at {OLLAMA_URL}")
    os.environ["SYSTEM_PROMPT_PATH"] = SYSTEM_PROMPT_PATH
    os.environ["OLLAMA_URL"] = OLLAMA_URL
    os.environ["OLLAMA_TIMEOUT"] = "120"  # CPU inference can be slow
    yield
    for key in ("SYSTEM_PROMPT_PATH", "OLLAMA_URL", "OLLAMA_TIMEOUT"):
        os.environ.pop(key, None)


def test_live_grounded_answer():
    from app import assistant
    result = assistant.ask("How often should diesel fleet vehicles have their oil changed?")
    lower = result.lower()
    assert any(kw in lower for kw in ["oil", "km", "000", "change", "interval", "diesel"]), \
        f"Expected grounded answer about oil, got: {result}"


def test_live_refusal_off_topic():
    from app import assistant
    result = assistant.ask("What is the weather in Tel Aviv today?")
    lower = result.lower()
    assert "fleet" in lower or "only" in lower or "weather" not in lower[:50], \
        f"Expected refusal, got: {result}"
