"""GuardrailProvider Protocol - the swap seam between Guardrails AI and Bedrock."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class GuardrailProvider(Protocol):
    def check_input(self, text: str, context: dict) -> dict: ...
    def check_output(self, text: str, sources: list[str]) -> dict: ...
