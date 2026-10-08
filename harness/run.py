"""Run every task: (optionally) run the agent, write the raw run journal to disk
BEFORE scoring, then four-field score and print a table.

    set -a; source .env; set +a
    python3 -m harness.run

The journal-before-scoring order is deliberate (S18): any score can be recomputed
from disk later without calling the model again.
"""
import json
import time
from pathlib import Path

from agent.client import Client
from . import verifiers as V
from .four_fields import Score, HEADER, verification_of
from .tasks import TASKS

RUNS = Path(__file__).parent / "runs"


def run_one(client, task):
    started = time.time()
    state = {}
    journal = {"task": task["id"], "desc": task["desc"], "started": started, "events": []}

    # ACT — run the agent for this task, if one is wired. Count the MCP calls IT makes.
    calls_before = client.ncalls
    if task["run"]:
        try:
            task["run"](client, state)
            journal["events"].append("agent ran")
        except Exception as e:
            journal["events"].append(f"agent error: {e}")
    agent_calls = client.ncalls - calls_before

    # VERIFY — read the DB and decide truth
    try:
        passed, evidence = task["verify"](client, state)
    except Exception as e:
        passed, evidence = False, f"verify error: {e}"

    # COST — real MCP calls the agent made (not the verifier's) + wall time
    cost = {"calls": agent_calls, "seconds": round(time.time() - started, 1)}

    # INTEGRITY — real check: did the run keep us inside our own company's data?
    try:
        integrity = "clean" if V.tenant_isolated(client) else "breach"
    except Exception:
        integrity = "unknown"

    # VERIFICATION — did the AGENT itself produce/confirm its own answer from the DB?
    verification = verification_of(bool(task["run"]), state, task.get("verify_key"))

    # JOURNAL TO DISK — before we score anything
    journal.update({"passed": passed, "evidence": evidence, "integrity": integrity,
                    "verification": verification, "cost": cost,
                    "trace": state.get("_trace"), "state_keys": list(state)})
    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{task['id']}.json").write_text(json.dumps(journal, indent=2))

    # SCORE
    return Score(
        task=task["id"],
        outcome="pass" if passed else "fail",
        integrity=integrity,
        verification=verification,
        cost=cost,
        evidence=evidence,
    )


def main():
    client = Client.login()
    scores = [run_one(client, t) for t in TASKS]
    print(HEADER)
    for s in scores:
        print(s.row())
    npass = sum(1 for s in scores if s.outcome == "pass")
    print(f"\n{npass}/{len(scores)} passed. Raw journals in {RUNS}/ (written before scoring).")


if __name__ == "__main__":
    main()
