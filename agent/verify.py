"""Verify -> refine (S17) for the Store Agent seat.

Re-reads the DB and confirms each goal's answer independently of what the agent said.
The DB-truth helpers are the single source both this verifier and the harness use.
"""
from agent import config
from agent.analyst import _rows, is_paid, is_shipped, PREPAID


def db_disagreements(client):
    """Ground truth for goal 2: numbers of prepaid orders shipped while unpaid."""
    orders = _rows(client, config.ORDER)
    return {o.get("number") for o in orders
            if is_shipped(o) and not is_paid(o) and o.get("payment_method") in PREPAID}


def db_launch_tie(client):
    """Ground truth for goal 1: does the launch coupon's used_count == orders using it?
    Returns True/False, or None if the launch coupon is not found."""
    coupons = _rows(client, config.COUPON)
    orders = _rows(client, config.ORDER)
    cp = next((c for c in coupons if c.get("code") == config.LAUNCH_COUPON_CODE), None)
    if not cp:
        return None
    used = sum(1 for o in orders if o.get("coupon_code") == config.LAUNCH_COUPON_CODE)
    return (cp.get("used_count") or 0) == used


def reality_check(client, state):
    goals = state.get("goals", [])
    out = {}
    if "coupon_ledger" in goals:
        want = db_launch_tie(client)
        got = state.get("coupon_ties")
        ok = want is not None and got == want
        out["coupon_ledger"] = {"ok": ok, "note": f"launch tie agent={got} db={want}"}
    if "payment_stock" in goals:
        want = db_disagreements(client)
        got = {d["number"] for d in state.get("disagreements", [])}
        ok = bool(got) and got == want
        out["payment_stock"] = {"ok": ok, "note": f"agent={len(got)} db={len(want)} match={ok}"}
    return {"ok": all(v["ok"] for v in out.values()) if out else True, "goals": out}


def run_verify(client, state):
    state["verify"] = reality_check(client, state)
