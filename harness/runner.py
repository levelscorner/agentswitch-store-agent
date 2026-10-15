"""Official AgentSwitch run entry point (Release 8.1): `python -m harness.runner`.

Everything comes from environment variables the course runner sets — no login, no
.env, no keys of our own:
  AGENTSWITCH_BASE_URL   the (fresh, throwaway) instance to call
  AGENTSWITCH_TOKEN      our seat's bearer token
  AGENTSWITCH_INSTANCE   suryodaya | keystone  (labels the task ids)

The storefront goals are pure DB reconciliation — no model is needed. This reuses our
real task set + DB-truth verifiers (harness/tasks.py, run_one) and writes results.json
in the grader's schema. Local rehearsal:

  set -a; source .env; set +a
  TOK=$(python -c "from agent.client import Client; print(Client.login()._token)")
  AGENTSWITCH_BASE_URL=https://agentswitch.theschoolofai.in \
  AGENTSWITCH_TOKEN=$TOK AGENTSWITCH_INSTANCE=suryodaya python -m harness.runner
"""
import json
import os

from agent.client import Client
from harness.run import run_one
from harness.tasks import TASKS


def main():
    base = os.environ["AGENTSWITCH_BASE_URL"].rstrip("/")
    client = Client(base, os.environ["AGENTSWITCH_TOKEN"])   # token, not login
    instance = os.environ.get("AGENTSWITCH_INSTANCE", "suryodaya")

    out = []
    for task in TASKS:
        score = run_one(client, task)          # runs the agent + DB-truth verify
        passed = score.outcome == "pass"
        out.append({
            "id": f"{instance}:{task['id']}",
            "title": task["desc"],
            "passed": bool(passed),
            "score": 1.0 if passed else 0.0,
            "evidence": str(score.evidence)[:500],
        })
        print(f"[{'PASS' if passed else 'FAIL'}] {task['id']}: {str(score.evidence)[:160]}", flush=True)

    npass = sum(1 for t in out if t["passed"])
    with open("results.json", "w") as fh:
        json.dump({"tasks": out,
                   "summary": f"{instance}: {npass}/{len(out)} tasks passed"}, fh, indent=2)
    print(f"\n{npass}/{len(out)} passed -> results.json", flush=True)


if __name__ == "__main__":
    main()
