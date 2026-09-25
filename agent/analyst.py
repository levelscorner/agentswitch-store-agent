"""Store Agent goal runners (team08 · Storefront).

Two goals from the seat brief:
  - coupon_ledger : how did the launch coupon do — does its usage tie to the ledger?
  - payment_stock : where do the payment records and the stock records disagree?

STATUS: the reconciliation SHAPE is here; the field arithmetic is wired after the
first login confirms entity/field names. Each runner PROBES its entities live and
stores a sample row's keys into state, so finishing the wiring is a one-edit step.
"""
from agent import config
from agent.client import MCPError


def _rows(client, entity, args=None):
    r = client.call(f"{entity}.list", args or {"limit": 200})
    if isinstance(r, list):
        return r
    return r.get("items", r.get("data", r.get("results", []))) if isinstance(r, dict) else []


def _probe(client, entity):
    """List an entity; return {'count', 'keys'} or {'error'} — never raises."""
    try:
        rows = _rows(client, entity)
        keys = sorted(rows[0].keys()) if rows and isinstance(rows[0], dict) else []
        return {"count": len(rows), "keys": keys}
    except MCPError as e:
        return {"error": str(e)}


def run_coupon_ledger(client, state):
    """Goal: how did the launch coupon do — does usage tie to the ledger?"""
    state["coupon_discovery"] = {e: _probe(client, e)
                                 for e in (config.COUPON, config.COUPON_LEDGER, config.ORDER)}
    # TODO(after login): find the launch coupon, count its redemptions on ORDER, sum the
    # COUPON_LEDGER entries for it, set state["coupon_ties"] = (redeemed == ledger_total).
    state.setdefault("_pending", []).append("coupon_ledger: confirm names, then reconcile usage vs ledger")
    return state


def run_payment_stock(client, state):
    """Goal: where do payment and stock disagree?"""
    state["payment_stock_discovery"] = {e: _probe(client, e)
                                        for e in (config.PAYMENT, config.STOCK, config.ORDER)}
    # TODO(after login): join PAYMENT and STOCK by order/product, collect rows where
    # paid-but-not-decremented (or decremented-but-unpaid), set state["disagreements"].
    state.setdefault("_pending", []).append("payment_stock: confirm names, then diff payment vs stock")
    return state
