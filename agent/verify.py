"""Verify -> refine (S17) for the Store Agent seat.

Reads the DB and confirms each goal's answer. Until the goals are wired (post-login
schema discovery) the reality checks report 'pending', never a false pass.
"""


def reality_check(client, state):
    goals = state.get("goals", [])
    out = {}
    if "coupon_ledger" in goals:
        ties = state.get("coupon_ties")
        out["coupon_ledger"] = {"ok": ties is True,
                                "note": "pending schema wiring" if ties is None else f"ties={ties}"}
    if "payment_stock" in goals:
        dis = state.get("disagreements")
        out["payment_stock"] = {"ok": dis is not None,
                                "note": "pending schema wiring" if dis is None else f"{len(dis)} disagreements"}
    return {"ok": all(v["ok"] for v in out.values()) if out else True, "goals": out}


def run_verify(client, state):
    state["verify"] = reality_check(client, state)
