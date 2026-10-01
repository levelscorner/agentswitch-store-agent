"""Concrete sub-agents (subgraphs) for the Store Agent seat (team08 · Storefront).

Both graded goals are now real sub-agents, not flat functions:
  - coupon_ledger : scoped to the launch coupon code; fetches coupons ‖ orders, reconciles,
                    assembles the tie + catalogue integrity signals.
  - payment_stock : fetches orders, detects prepaid-shipped-unpaid disagreements.
Each gets only a scoped input, runs its own internal DAG, and returns only its declared
outputs. Its reads/scratch (`_coupons`, `_orders`, candidates) stay private to the subgraph.
"""
from agent import config
from agent.dag import DAG, Node
from agent.subgraph import Subgraph
from agent.analyst import _rows, is_paid, is_shipped, PREPAID


# --- coupon_ledger sub-agent --------------------------------------------------

def _cl_fetch_coupons(ctx, s):
    s["_coupons"] = _rows(ctx.client, config.COUPON)


def _cl_fetch_orders(ctx, s):
    s["_orders"] = _rows(ctx.client, config.ORDER)


def _cl_reconcile(ctx, s):
    used = {}
    for o in s.get("_orders") or []:
        code = o.get("coupon_code")
        if code:
            used[code] = used.get(code, 0) + 1
    s["_used_by_code"] = used


def _cl_assemble(ctx, s):
    coupons = s.get("_coupons") or []
    used = s.get("_used_by_code") or {}
    launch = next((cp for cp in coupons if cp.get("code") == s.get("launch_coupon_code")), None)
    if launch:
        orders_using = used.get(launch.get("code"), 0)
        s["launch_coupon"] = {
            "code": launch.get("code"), "used_count": launch.get("used_count"),
            "usage_limit": launch.get("usage_limit"), "orders_using": orders_using,
            "ties": (launch.get("used_count") or 0) == orders_using,
        }
        s["coupon_ties"] = s["launch_coupon"]["ties"]
    s["coupon_ledger_untied"] = sum(
        1 for cp in coupons if (cp.get("used_count") or 0) != used.get(cp.get("code"), 0))
    s["coupons_over_limit"] = [
        cp.get("code") for cp in coupons
        if (cp.get("usage_limit") or 0) > 0 and (cp.get("used_count") or 0) > cp.get("usage_limit")]


def _build_coupon_ledger():
    return (DAG(max_workers=2)
            .add(Node("fetch_coupons", _cl_fetch_coupons))
            .add(Node("fetch_orders", _cl_fetch_orders))
            .add(Node("reconcile", _cl_reconcile, deps=["fetch_orders"]))
            .add(Node("assemble", _cl_assemble, deps=["fetch_coupons", "reconcile"])))


coupon_ledger_subgraph = Subgraph(
    name="coupon_ledger",
    inputs=["launch_coupon_code"],
    outputs=["launch_coupon", "coupon_ties", "coupon_ledger_untied", "coupons_over_limit"],
    build=_build_coupon_ledger,
)


# --- payment_stock sub-agent --------------------------------------------------

def _ps_fetch(ctx, s):
    s["_orders"] = _rows(ctx.client, config.ORDER)


def _ps_detect(ctx, s):
    s.merge("disagreement_candidates", [
        {"number": o.get("number"), "payment_method": o.get("payment_method"),
         "status": o.get("status"), "tracking_number": o.get("tracking_number")}
        for o in (s.get("_orders") or [])
        if is_shipped(o) and not is_paid(o) and o.get("payment_method") in PREPAID])


def _ps_assemble(ctx, s):
    s["disagreements"] = s.get("disagreement_candidates") or []


def _build_payment_stock():
    return (DAG(max_workers=1)
            .add(Node("fetch", _ps_fetch))
            .add(Node("detect", _ps_detect, deps=["fetch"]))
            .add(Node("assemble", _ps_assemble, deps=["detect"])))


payment_stock_subgraph = Subgraph(
    name="payment_stock",
    inputs=[],
    outputs=["disagreements"],
    build=_build_payment_stock,
)
