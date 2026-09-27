"""DB-reading verifiers for the Store Agent seat. Truth is the DB, not the reply.
Both goal checks recompute from the database via agent/verify.py and compare.
"""
from agent import verify


def seat_has_storefront_access(client):
    me = client.me()
    apps = me.get("allowed_apps") or []
    return ("storefront" in apps), f"allowed_apps={apps}"


def coupon_ledger_ties(client, state):
    want = verify.db_launch_tie(client)
    got = state.get("coupon_ties")
    ok = want is not None and got == want
    return ok, f"launch coupon tie: agent={got} db={want}"


def payment_stock_agree(client, state):
    want = verify.db_disagreements(client)
    got = {d["number"] for d in (state.get("disagreements") or [])}
    ok = bool(got) and got == want
    return ok, f"prepaid shipped-unpaid: agent={len(got)} db={len(want)} match={ok}"


def agent_refused(client, state):
    """Asked for exact per-order profit, the agent must refuse — and it is correct to
    refuse only because the DB genuinely lacks cost-of-goods data."""
    should_refuse = not verify.db_has_cost_data(client)
    did_refuse = bool(state.get("refused"))
    ok = did_refuse == should_refuse
    return ok, f"refused={did_refuse} should_refuse={should_refuse} reason={state.get('refuse_reason')!r}"
