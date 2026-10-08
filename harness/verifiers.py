"""DB-reading verifiers for the Store Agent seat. Truth is the DB, not the reply.
Both goal checks recompute from the database via agent/verify.py and compare.
"""
from agent import verify, config
from agent.analyst import _rows


def seat_has_storefront_access(client):
    me = client.me()
    apps = me.get("allowed_apps") or []
    return ("storefront" in apps), f"allowed_apps={apps}"


def _untied_count(coupons, orders):
    """Coupons whose used_count != the number of orders that actually used them — recomputed
    here, independently of the agent's subgraph. This is the real 'the usage counter is
    disconnected from orders' finding (phantom usage)."""
    used = {}
    for o in orders:
        code = o.get("coupon_code")
        if code:
            used[code] = used.get(code, 0) + 1
    return sum(1 for cp in coupons
               if (cp.get("used_count") or 0) != used.get(cp.get("code"), 0))


def coupon_ledger_ties(client, state):
    """Goal 1: the launch coupon's usage ties to the ledger — AND the ledger as a whole.
    Independently recomputed: the launch tie, plus the count of coupons whose used_count does
    NOT match the orders that used them. The second check makes the goal non-vacuous — the
    launch coupon alone can tie trivially at 0==0 while the ledger is systemically broken."""
    want_tie = verify.db_launch_tie(client)
    got_tie = state.get("coupon_ties")
    want_untied = _untied_count(_rows(client, config.COUPON), _rows(client, config.ORDER))
    got_untied = state.get("coupon_ledger_untied")
    ok = (want_tie is not None and got_tie == want_tie and got_untied == want_untied)
    return ok, (f"launch tie agent={got_tie} db={want_tie}; "
                f"coupons untied agent={got_untied} db={want_untied}")


def payment_stock_agree(client, state):
    want = verify.db_disagreements(client)
    got = {d["number"] for d in (state.get("disagreements") or [])}
    ok = (got == want)   # a correct EMPTY answer must pass too — never require bool(got)
    return ok, f"prepaid shipped-unpaid: agent={len(got)} db={len(want)} match={ok}"


def agent_refused(client, state):
    """Asked for exact per-order profit, the agent must refuse — and it is correct to
    refuse only because the DB genuinely lacks cost-of-goods data."""
    should_refuse = not verify.db_has_cost_data(client)
    did_refuse = bool(state.get("refused"))
    ok = did_refuse == should_refuse
    return ok, f"refused={did_refuse} should_refuse={should_refuse} reason={state.get('refuse_reason')!r}"


def _single_tenant(rows, id_field="company_id"):
    """True iff every row belongs to one company — no cross-tenant leak."""
    ids = {r.get(id_field) for r in rows if r.get(id_field)}
    return len(ids) <= 1


def tenant_isolated(client):
    """Integrity signal: the seat sees only our own company's orders, not another's."""
    return _single_tenant(_rows(client, config.ORDER))


def trace_recorded(trace):
    """A run is observable iff it recorded per-node timings AND the dag order."""
    t = trace or {}
    return bool(t.get("timings")) and bool(t.get("dag_order"))


def agent_recorded_a_trace(client, state):
    """Observability (S18): the agent's run must surface a per-node timing trace."""
    t = state.get("_trace") or {}
    nodes = list((t.get("timings") or {}).keys())
    return trace_recorded(t), f"trace nodes={nodes} order={t.get('dag_order')}"
