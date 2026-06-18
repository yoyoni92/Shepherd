"""T1 - Client contract: ask() calls Ollama with system prompt, returns text, handles timeout."""
import os
import pytest
from unittest.mock import patch, MagicMock
import httpx


@pytest.fixture(autouse=True)
def prompt_env(tmp_path):
    p = tmp_path / "system.txt"
    p.write_text("You are a fleet assistant.")
    os.environ["SYSTEM_PROMPT_PATH"] = str(p)
    os.environ["OLLAMA_URL"] = "http://fake-ollama:11434"
    yield
    os.environ.pop("SYSTEM_PROMPT_PATH", None)
    os.environ.pop("OLLAMA_URL", None)


def _mock_response(content: str):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {"message": {"role": "assistant", "content": content}}
    resp.raise_for_status = MagicMock()
    return resp


def test_ask_prepends_system_prompt():
    with patch("httpx.post", return_value=_mock_response("ok")) as mock_post:
        from app import assistant
        assistant.ask("test question")

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["messages"][0]["role"] == "system"
        assert call_json["messages"][0]["content"] == "You are a fleet assistant."
        assert call_json["messages"][1]["role"] == "user"
        assert call_json["messages"][1]["content"] == "test question"


def test_ask_returns_text():
    with patch("httpx.post", return_value=_mock_response("Rotate every 10,000 km.")):
        from app import assistant
        result = assistant.ask("How often to rotate tires?")
        assert result == "Rotate every 10,000 km."


def test_ask_raises_timeout():
    with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
        from app import assistant
        with pytest.raises(TimeoutError):
            assistant.ask("any question")


def test_ask_calls_correct_ollama_endpoint():
    with patch("httpx.post", return_value=_mock_response("ok")) as mock_post:
        from app import assistant
        assistant.ask("any question")
        url = mock_post.call_args.args[0]
        assert url == "http://fake-ollama:11434/api/chat"
