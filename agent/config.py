"""Config for the Store Agent seat (team08 · Storefront). Read from the environment.

The entity names below are DOMAIN GUESSES from the seat brief. Confirm each against
the live `tools/list` on first login (`python3 -m agent.client`) and correct any that
differ — that is the one wiring step before the two goals can run for real.
"""
import os

AS_BASE = os.environ.get("AS_BASE", "https://agentswitch.theschoolofai.in").rstrip("/")
AS_EMAIL = os.environ.get("AS_EMAIL", "team08@theschoolofai.in")

# Storefront entities — CONFIRMED live 2026-09-25 (tools/list).
COUPON = os.environ.get("SF_COUPON", "Coupon")     # code, type, value, usage_limit, used_count, valid_from/to, is_active
ORDER  = os.environ.get("SF_ORDER", "WebOrder")    # D2C order: coupon_code/coupon_discount +
#   payment (funding_amount, funding_mode, payment_method, payment_failure_reason, payment_gateway_*) +
#   fulfillment (status, tracking_number, items). status flow: pending_payment→(confirm_payment)→process→ship→mark_delivered.
# NOTE: there is NO separate CouponLedger / Payment / Stock entity — both goals reconcile
# WITHIN Coupon + WebOrder. StockAlert exists but is empty; product/stock detail rides on WebOrder.items.

# Launch-coupon candidates are the human-named codes (vs auto-generated like "VC8379/1862"):
# WELCOME10 (10%), BULK20 (20%), FREESHIP. Set the real one once the brief/UI names it.
LAUNCH_COUPON_CODE = os.environ.get("SF_LAUNCH_COUPON", "WELCOME10")

# The two graded goals for this seat (from the brief).
GOAL_IDS = ("storefront.coupon_ledger_ties", "storefront.payment_stock_agree")
