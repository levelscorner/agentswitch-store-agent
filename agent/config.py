"""Config for the Store Agent seat (team08 · Storefront). Read from the environment.

The entity names below are DOMAIN GUESSES from the seat brief. Confirm each against
the live `tools/list` on first login (`python3 -m agent.client`) and correct any that
differ — that is the one wiring step before the two goals can run for real.
"""
import os

AS_BASE = os.environ.get("AS_BASE", "https://agentswitch.theschoolofai.in").rstrip("/")
AS_EMAIL = os.environ.get("AS_EMAIL", "team08@theschoolofai.in")

# Storefront entities — CONFIRM via tools/list, then fix any that differ.
COUPON        = os.environ.get("SF_COUPON", "Coupon")
COUPON_LEDGER = os.environ.get("SF_COUPON_LEDGER", "CouponLedger")
ORDER         = os.environ.get("SF_ORDER", "Order")
PAYMENT       = os.environ.get("SF_PAYMENT", "Payment")
STOCK         = os.environ.get("SF_STOCK", "StockItem")

# The launch coupon to analyse for `coupon_ledger_ties` — set once discovered.
LAUNCH_COUPON_CODE = os.environ.get("SF_LAUNCH_COUPON", "")

# The two graded goals for this seat (from the brief).
GOAL_IDS = ("storefront.coupon_ledger_ties", "storefront.payment_stock_agree")
