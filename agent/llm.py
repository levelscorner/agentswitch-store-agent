"""LLM wrapper (Anthropic SDK) with model routing (S15) + reliability (S12).

Model routing: cheap tier for simple work (plan, draft), strong tier for hard
judgment (verify). Config, not code:
  MODEL_SIMPLE (default Haiku)  ·  MODEL_HARD (default Opus)  ·  AGENT_MODEL pins both.

Reliability: transient API errors retry with backoff; a per-run Breaker (set via
set_breaker) caps total calls and opens after repeated failures.
"""
import os

import anthropic

from agent import reliability

MODELS = {
    "simple": os.environ.get("MODEL_SIMPLE", "claude-haiku-4-5"),
    "hard": os.environ.get("MODEL_HARD", "claude-opus-5"),
}
_OVERRIDE = os.environ.get("AGENT_MODEL")  # pins both tiers when set

_TRANSIENT = tuple(
    getattr(anthropic, n) for n in
    ("APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError")
    if hasattr(anthropic, n)
) or (Exception,)

_client = None
_BREAKER = None  # per-run guard; set by respond.respond()


def _get():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def set_breaker(b):
    """Install the per-run budget/circuit breaker (or None to disable)."""
    global _BREAKER
    _BREAKER = b


def _model(tier):
    return _OVERRIDE or MODELS.get(tier, MODELS["hard"])


def draft(system, prompt, tier="simple", max_tokens=4000):
    """Return (text, usage). Routes by tier, retries transient API errors with
    backoff, and counts against the run breaker."""
    model = _model(tier)

    def call():
        return _get().messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        )

    resp = reliability.call_with_retries(call, transient=_TRANSIENT, breaker=_BREAKER)
    text = "".join(b.text for b in resp.content if b.type == "text")
    usage = {"model": model, "in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
    return text, usage


def draft_json(system, prompt, tier="simple", max_tokens=800):
    """Draft and parse JSON. On invalid JSON, ask the model once to repair it."""
    text, _ = draft(system, prompt, tier=tier, max_tokens=max_tokens)
    try:
        return reliability.extract_json(text)
    except Exception:
        fixed, _ = draft("Return ONLY valid JSON, no prose.",
                         "Fix this into valid JSON:\n" + text, tier="simple", max_tokens=max_tokens)
        return reliability.extract_json(fixed)
