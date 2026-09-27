"""Store Agent goal runners (team08 · Storefront). Wired live 2026-09-25.

  - coupon_ledger : does the launch coupon's used_count tie to the orders that used it?
  - payment_stock : which orders shipped (stock moved) while still unpaid — the real
                    disagreement, excluding cash-on-delivery where that is legitimate.

Grading reads the DB (agent/verify.py recomputes independently); these produce the answer.
"""
from agent import config
from agent.client import MCPError

# Prepaid methods: for these, a tracking number on an unpaid order is a genuine
# payment/stock disagreement. COD legitimately ships before payment, so it is excluded.
PREPAID = {"razorpay", "card", "ach", "check", "bank_transfer"}
_PAID_STATES = ("paid", "processing", "shipped", "delivered", "confirmed")
_SHIPPED_STATES = ("shipped", "delivered")


def _rows(client, entity, args=None):
    r = client.call(f"{entity}.list", args or {"limit": 500})
    if isinstance(r, list):
        return r
    return r.get("items", r.get("data", r.get("results", []))) if isinstance(r, dict) else []


def is_paid(o):
    return bool(o.get("funding_amount")) or o.get("status") in _PAID_STATES


def is_shipped(o):
    return bool(o.get("tracking_number")) or o.get("status") in _SHIPPED_STATES


def run_coupon_ledger(client, state):
    """Goal 1: how did the launch coupon do — does used_count tie to real orders?"""
    coupons = _rows(client, config.COUPON)
    orders = _rows(client, config.ORDER)
    used_by_code = {}
    for o in orders:
        code = o.get("coupon_code")
        if code:
            used_by_code[code] = used_by_code.get(code, 0) + 1

    launch = next((cp for cp in coupons if cp.get("code") == config.LAUNCH_COUPON_CODE), None)
    if launch:
        orders_using = used_by_code.get(launch.get("code"), 0)
        state["launch_coupon"] = {
            "code": launch.get("code"),
            "used_count": launch.get("used_count"),
            "usage_limit": launch.get("usage_limit"),
            "orders_using": orders_using,
            "ties": (launch.get("used_count") or 0) == orders_using,
        }
        state["coupon_ties"] = state["launch_coupon"]["ties"]

    # catalogue-wide integrity signals (feed the bug hunt)
    state["coupon_ledger_untied"] = sum(
        1 for cp in coupons if (cp.get("used_count") or 0) != used_by_code.get(cp.get("code"), 0))
    state["coupons_over_limit"] = [
        cp.get("code") for cp in coupons
        if (cp.get("usage_limit") or 0) > 0 and (cp.get("used_count") or 0) > cp.get("usage_limit")]
    return state


def run_payment_stock(client, state):
    """Goal 2: prepaid orders that shipped (stock moved) while still unpaid."""
    orders = _rows(client, config.ORDER)
    dis = [
        {"number": o.get("number"), "payment_method": o.get("payment_method"),
         "status": o.get("status"), "tracking_number": o.get("tracking_number")}
        for o in orders
        if is_shipped(o) and not is_paid(o) and o.get("payment_method") in PREPAID
    ]
    state["disagreements"] = dis
    return state


def db_has_cost_data(client):
    """Ground truth: does the storefront expose cost of goods for any product?"""
    items = _rows(client, "Item")
    return any((it.get("purchase_rate") or 0) > 0 or (it.get("standard_rate") or 0) > 0 for it in items)


def run_refusal(client, state):
    """Refusal goal: asked for EXACT per-order profit/margin, which needs cost of goods.
    The storefront exposes revenue (grand_total/subtotal) but Item.purchase_rate /
    standard_rate are unset across the catalogue, so profit cannot be computed. The
    honest answer is to refuse, not invent a number. If cost data ever appears, the
    agent should compute instead of refusing — so this checks the DB before refusing."""
    if db_has_cost_data(client):
        state["refused"] = False
        state["refuse_reason"] = ""
    else:
        state["refused"] = True
        state["refuse_reason"] = (
            "The storefront exposes order revenue (grand_total, subtotal) but no cost of goods — "
            "Item.purchase_rate and standard_rate are unset across the catalogue — so exact per-order "
            "profit or margin cannot be computed from this seat's data. Reporting a figure would be inventing it."
        )
    return state
