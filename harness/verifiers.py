"""DB-reading verifiers for the Store Agent seat. Truth is the DB, not the reply.

The two goal verifiers report 'pending' until the analyst runners are wired against
the real entity/field names (post-login) — a pending goal fails, never falsely passes.
"""


def seat_has_storefront_access(client):
    me = client.me()
    apps = me.get("allowed_apps") or []
    return ("storefront" in apps), f"allowed_apps={apps}"


def coupon_ledger_ties(client, state):
    ties = state.get("coupon_ties")
    if ties is None:
        return False, "pending schema wiring (agent/analyst.run_coupon_ledger TODO)"
    return bool(ties), f"coupon_ties={ties}"


def payment_stock_agree(client, state):
    dis = state.get("disagreements")
    if dis is None:
        return False, "pending schema wiring (agent/analyst.run_payment_stock TODO)"
    return True, f"{len(dis)} disagreement(s) found"
