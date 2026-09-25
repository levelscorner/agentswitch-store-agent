"""Stable integration seam for an external harness (S18).

The course's Week-2 harness will drive our agent with a task prompt and read the
result. This is the ONE file that maps their contract to ours, so wiring their
spec in is a single-file change instead of a hunt through the agent.

Two ways in:
  - import:  from harness.adapter import run;  run("Publish ... which pages nobody reads?")
  - shell:   echo '{"prompt":"..."}' | python3 -m harness.adapter    # JSON in -> JSON out

Output contract (JSON):
  { ok, task_id, plan, answer, verify, seconds }

`ok`/`verify` come from re-reading the DB (agent/verify.py) — that is the truth a
grader should score. `answer` is the human-facing text and is never the ground truth.
"""
import json
import sys
import time

from agent.client import Client
from agent import respond as _respond


def run(prompt, client=None, task_id=None):
    """Run the full agent pipeline for one prompt and return the graded contract.

    Pass a logged-in `client` to reuse a session (the external harness usually owns
    the auth); omit it and we log in from the environment.
    """
    started = time.time()
    client = client or Client.login()
    plan, answer, state = _respond.respond(prompt, client=client)
    verify = state.get("verify") or {}
    return {
        "ok": bool(verify.get("ok", True)),
        "task_id": task_id,
        "plan": plan,
        "answer": answer,
        "verify": verify,
        "seconds": round(time.time() - started, 1),
    }


def _read_request():
    """Prompt from stdin JSON, else argv, else the default graded sentence."""
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            try:
                obj = json.loads(raw)
                return obj.get("prompt", ""), obj.get("task_id")
            except Exception:
                return raw, None  # treat a bare line as the prompt
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]), None
    return ("Publish a post about the new fixture line, "
            "and tell me which pages nobody reads."), None


def main():
    prompt, task_id = _read_request()
    print(json.dumps(run(prompt, task_id=task_id), indent=2))


if __name__ == "__main__":
    main()
