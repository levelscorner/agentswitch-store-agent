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
    """Goal 1 now runs as a sub-agent. Compatibility entry point (the harness and any legacy
    caller use it): hand the coupon_ledger subgraph a scoped input, copy its outputs back."""
    from agent.subgraphs import coupon_ledger_subgraph   # local import avoids an import cycle
    state.update(coupon_ledger_subgraph.run(client, {"launch_coupon_code": config.LAUNCH_COUPON_CODE}))


def run_payment_stock(client, state):
    """Goal 2 now runs as a sub-agent. Compatibility entry point (harness/legacy)."""
    from agent.subgraphs import payment_stock_subgraph   # local import avoids an import cycle
    state.update(payment_stock_subgraph.run(client, {}))


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
