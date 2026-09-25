"""Natural-language entrypoint for the Store Agent seat (team08 · Storefront).

    set -a; source .env.team08; set +a
    python3 -m agent.respond "How did the launch coupon do, and where do payment and stock disagree?"

Same S05 planner + S08 DAG + S17 verify backbone as the Website seat; only the GOALS
and the planner prompt are storefront-specific.
"""
import sys
from types import SimpleNamespace

from agent import llm, memory, reliability, verify
from agent.client import Client
from agent.dag import DAG, Node
from agent.analyst import run_coupon_ledger, run_payment_stock

GOALS = {"coupon_ledger": run_coupon_ledger, "payment_stock": run_payment_stock}

PLANNER_SYSTEM = (
    "You route a storefront-agent request to goals. Available goals:\n"
    "  coupon_ledger  - how did the launch coupon do / did coupon usage tie to the ledger\n"
    "  payment_stock  - where do payment records and stock records disagree\n"
    'Return STRICT JSON only: {"goals": [ ... ]} in the order they should run.'
)


def plan(prompt):
    try:
        data = llm.draft_json(PLANNER_SYSTEM, prompt, tier="simple", max_tokens=200)
        goals = [g for g in data.get("goals", []) if g in GOALS]
        if goals:
            return goals
    except Exception:
        pass
    return _keyword_plan(prompt)


def _keyword_plan(prompt):
    p = prompt.lower()
    goals = []
    if any(w in p for w in ("coupon", "launch", "ledger", "discount")):
        goals.append("coupon_ledger")
    if any(w in p for w in ("payment", "stock", "inventory", "disagree", "mismatch")):
        goals.append("payment_stock")
    return goals or ["coupon_ledger", "payment_stock"]


def build_dag(goals):
    dag = DAG(max_workers=3)
    for g in goals:
        fn = GOALS[g]
        dag.add(Node(g, lambda ctx, s, fn=fn: fn(ctx.client, s)))
    dag.add(Node("verify", lambda ctx, s: verify.run_verify(ctx.client, s), deps=list(goals)))
    return dag


def compose(state):
    parts = []
    lc = state.get("launch_coupon")
    if lc:
        parts.append(
            f"Launch coupon {lc['code']}: used_count={lc['used_count']} vs {lc['orders_using']} "
            f"orders that used it → {'ties' if lc['ties'] else 'DOES NOT tie'}. "
            f"Catalogue: {state.get('coupon_ledger_untied', 0)} coupons untied, "
            f"{len(state.get('coupons_over_limit', []))} over their usage_limit.")
    dis = state.get("disagreements")
    if dis is not None:
        sample = [d["number"] for d in dis[:5]]
        parts.append(f"Payment vs stock: {len(dis)} prepaid order(s) shipped while unpaid"
                     + (f" — e.g. {sample}" if sample else " — none"))
    v = state.get("verify")
    if v and v.get("goals"):
        parts.append("Verified against the DB: " + "; ".join(
            f"{g} {'OK' if r['ok'] else 'PENDING (' + r['note'] + ')'}" for g, r in v["goals"].items()))
    return "\n\n".join(parts) or "No goal matched that request."


def respond(prompt, client=None):
    client = client or Client.login()
    llm.set_breaker(reliability.Breaker())
    mem = memory.Memory(client).seed_defaults()
    goals = plan(prompt)
    state = {"prompt": prompt, "goals": goals}
    ctx = SimpleNamespace(client=client, memory=mem)
    build_dag(goals).run(ctx, state)
    return goals, compose(state), state


def main():
    prompt = " ".join(sys.argv[1:]) or "How did the launch coupon do, and where do payment and stock disagree?"
    goals, answer, _ = respond(prompt)
    print(f"PROMPT: {prompt}\nPLAN:   {goals}\n\n{answer}")


if __name__ == "__main__":
    main()
