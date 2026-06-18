"""Guardrails AI provider - topic + grounding rails via guardrails-ai hub validators.

# ponytail: rails/ directory skipped; topic/grounding configs inlined here.
# ponytail: guards are lazy singletons - hub imports are heavy and need API keys.
"""
from __future__ import annotations

import os

from app.base import GuardrailProvider  # noqa: F401


FLEET_TOPICS = [
    "fleet management", "vehicle", "driver", "maintenance", "km update",
    "insurance", "accident", "ticket", "fine", "license", "mileage",
    "רכב", "נהג", "ביטוח", "תאונה", "קילומטראז", "רישיון",
]

# V5 of the topic restriction prompt (see PROMPT_LOG.md for full history)
TOPIC_SYSTEM_PROMPT = (
    "You are a fleet management assistant. Determine if the input relates to "
    "fleet topics: vehicles, drivers, maintenance, mileage, insurance, accidents, "
    "fines, or licenses. Hebrew and English inputs are both valid. "
    "Respond only 'yes' (fleet-related) or 'no' (off-topic)."
)

# V5 of the grounding prompt (see PROMPT_LOG.md for full history)
GROUNDING_SYSTEM_PROMPT = (
    "You are a fact-checker. Given source documents and a generated response, "
    "determine if every factual claim (price, date, legal requirement, fine amount, "
    "regulation number) is explicitly supported by the source documents. "
    "Respond only 'yes' (fully grounded) or 'no' (contains unsupported claims)."
)

_input_guard = None
_output_guard = None


def _get_input_guard():
    global _input_guard
    if _input_guard is None:
        from guardrails import Guard, OnFailAction
        from guardrails.hub import RestrictToTopic, ToxicLanguage

        _input_guard = (
            Guard()
            .use(
                RestrictToTopic,
                valid_topics=FLEET_TOPICS,
                disable_classifier=True,
                llm_callable=os.environ.get("GUARDRAILS_LLM", "openai/gpt-4o-mini"),
                on_fail=OnFailAction.NOOP,
            )
            .use(ToxicLanguage, threshold=0.5, on_fail=OnFailAction.NOOP)
        )
    return _input_guard


def _get_output_guard():
    global _output_guard
    if _output_guard is None:
        from guardrails import Guard, OnFailAction
        from guardrails.hub import ProvenanceV1

        _output_guard = (
            Guard()
            .use(
                ProvenanceV1,
                llm_callable=os.environ.get("GUARDRAILS_LLM", "openai/gpt-4o-mini"),
                on_fail=OnFailAction.FIX,
            )
        )
    return _output_guard


class GuardrailsAIProvider:
    def check_input(self, text: str, context: dict) -> dict:
        outcome = _get_input_guard().validate(text)
        if outcome.validation_passed:
            return {"pass": True, "reason": "ok"}
        return {"pass": False, "reason": outcome.error or "input validation failed"}

    def check_output(self, text: str, sources: list[str]) -> dict:
        outcome = _get_output_guard().validate(
            text, metadata={"sources": sources, "source_field": "sources"}
        )
        if outcome.validation_passed:
            return {"pass": True, "reason": "ok"}
        return {
            "pass": False,
            "reason": outcome.error or "output grounding failed",
            "safe_text": outcome.validated_output or "",
        }


class BedrockGuardrailsStub:
    """Swap-in for AWS Bedrock Guardrails. Conforms to GuardrailProvider.

    # ponytail: wire to boto3 bedrock.apply_guardrail() when switching providers.
    """

    def check_input(self, text: str, context: dict) -> dict:
        raise NotImplementedError("wire to boto3 bedrock.apply_guardrail()")

    def check_output(self, text: str, sources: list[str]) -> dict:
        raise NotImplementedError("wire to boto3 bedrock.apply_guardrail()")
