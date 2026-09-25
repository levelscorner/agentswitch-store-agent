"""Reliability layer (S12): retries with backoff, JSON repair, and a per-run
circuit breaker + budget cap. Wraps the flaky model calls so one bad response
or a transient API blip doesn't crash — or bankrupt — a run.

Two different failures, two guards:
  - transient (network / 429 / 5xx) -> retry with exponential backoff
  - repeated failure or over budget  -> breaker trips, the run stops cleanly
"""
import json
import threading
import time


class BudgetExceeded(RuntimeError):
    """The run hit its call cap or the breaker opened after repeated failures."""


class Breaker:
    """A per-run guard shared across parallel nodes. Caps total model calls and
    opens after too many consecutive failures. Thread-safe, because the DAG runs
    nodes on a small pool and they all draw from one budget."""

    def __init__(self, max_calls=12, max_consec_fails=3):
        self.max_calls = max_calls
        self.max_consec_fails = max_consec_fails
        self.calls = 0
        self.consec_fails = 0
        self._lock = threading.Lock()

    def before(self):
        with self._lock:
            if self.calls >= self.max_calls:
                raise BudgetExceeded(f"budget cap hit ({self.max_calls} model calls)")
            if self.consec_fails >= self.max_consec_fails:
                raise BudgetExceeded(f"circuit breaker open ({self.consec_fails} consecutive failures)")
            self.calls += 1

    def ok(self):
        with self._lock:
            self.consec_fails = 0

    def fail(self):
        with self._lock:
            self.consec_fails += 1


def call_with_retries(fn, *, tries=3, base_delay=0.6, transient=(Exception,), breaker=None):
    """Call fn(); retry transient failures with exponential backoff. A breaker,
    if given, counts each attempt (and can open before the call is even made)."""
    last = None
    for attempt in range(tries):
        if breaker:
            breaker.before()            # raises BudgetExceeded -> propagates, not retried
        try:
            out = fn()
            if breaker:
                breaker.ok()
            return out
        except transient as e:
            last = e
            if breaker:
                breaker.fail()
            if attempt == tries - 1:
                break
            time.sleep(base_delay * (2 ** attempt))
    raise last


def extract_json(text):
    """Pull the first {...} block out of model text and parse it."""
    return json.loads(text[text.index("{"):text.rindex("}") + 1])
