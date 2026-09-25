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
from .four_fields import Score, HEADER
from .tasks import TASKS

RUNS = Path(__file__).parent / "runs"


def run_one(client, task):
    started = time.time()
    state = {}
    journal = {"task": task["id"], "desc": task["desc"], "started": started, "events": []}

    # ACT — run the agent for this task, if one is wired
    if task["run"]:
        try:
            task["run"](client, state)
            journal["events"].append("agent ran")
        except Exception as e:
            journal["events"].append(f"agent error: {e}")

    # VERIFY — read the DB and decide truth
    try:
        passed, evidence = task["verify"](client, state)
    except Exception as e:
        passed, evidence = False, f"verify error: {e}"

    cost = {"seconds": round(time.time() - started, 1)}

    # JOURNAL TO DISK — before we score anything
    journal.update({"passed": passed, "evidence": evidence, "cost": cost, "state_keys": list(state)})
    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{task['id']}.json").write_text(json.dumps(journal, indent=2))

    # SCORE
    return Score(
        task=task["id"],
        outcome="pass" if passed else "fail",
        verification=("verified" if task["run"] else "n/a"),
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
