"""Store Agent task set (team08 · Storefront). Read-only seat check passes at login;
the two goal tasks go green once the runners are wired against real schemas.
"""
from . import verifiers as V
from agent.analyst import run_coupon_ledger, run_payment_stock


TASKS = [
    {
        "id": "seat_access",
        "desc": "our seat can use the storefront app",
        "run": None,
        "verify": lambda c, s: V.seat_has_storefront_access(c),
    },
    {
        "id": "coupon_ledger_ties",
        "desc": "launch coupon usage ties to the ledger (Goal #1)",
        "run": run_coupon_ledger,
        "verify": lambda c, s: V.coupon_ledger_ties(c, s),
    },
    {
        "id": "payment_stock_agree",
        "desc": "payment/stock disagreements identified (Goal #2)",
        "run": run_payment_stock,
        "verify": lambda c, s: V.payment_stock_agree(c, s),
    },
]
