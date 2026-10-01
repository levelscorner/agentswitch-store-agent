"""Daily probe-and-draft bug hunt (team08 · Storefront).

Read-only by design, so it is safe to run unattended: it reads the live DB, flags
data signals that indicate an un-enforced rule, detects newly-appeared entities, DRAFTS
any candidate into docs/bug-reports/ (gitignored), prints a summary, and FILES NOTHING.
You review the draft and file via the bug button / API. Deeper write-tests live in the
manual sweep, not here.

    set -a; source .env; set +a
    python3 -m harness.daily_hunt

Schedule locally (cron, 9am daily):
    0 9 * * * cd ~/ws/projects/agentswitch-store-agent && set -a && . ./.env && set +a && \
      /usr/bin/python3 -m harness.daily_hunt >> ~/.agentswitch-hunt-a08.log 2>&1
"""
import datetime
import json
import pathlib

from agent.client import Client
from agent import config

RUNS = pathlib.Path(__file__).parent / "runs"


def _rows(c, e, a=None):
    r = c.call(f"{e}.list", a or {"limit": 500})
    return r if isinstance(r, list) else r.get("items", r.get("data", r.get("results", [])))


def check_coupon_counter(c):
    coupons = _rows(c, config.COUPON)
    over = [cp.get("code") for cp in coupons
            if (cp.get("usage_limit") or 0) > 0 and (cp.get("used_count") or 0) > cp.get("usage_limit")]
    if over:
        return "BUG", (f"{len(over)} coupons have used_count > usage_limit — the counter is client-settable "
                       f"and the cap is unenforced (e.g. {over[:5]})")
    return "secure", "no coupon exceeds its usage_limit"


def check_item_mrp(c):
    items = _rows(c, "Item")
    over = [i for i in items
            if (i.get("selling_price") or 0) > 0 and (i.get("mrp") or 0) > 0
            and i.get("selling_price") > i.get("mrp")]
    withmrp = sum(1 for i in items if (i.get("mrp") or 0) > 0)
    if over:
        return "BUG", (f"{len(over)} of {withmrp} priced items have selling_price > mrp — "
                       f"the storefront allows selling above Maximum Retail Price")
    return "secure", "no item sells above its MRP"


def check_tenant_isolation(c):
    myco = c.me().get("company_id")
    foreign = [o for o in _rows(c, config.ORDER) if o.get("company_id") not in (myco, None)]
    if foreign:
        return "BUG", f"{len(foreign)} foreign-company WebOrders visible to our seat (tenant leak)"
    return "secure", "only our company's orders are visible"


def monitor_payment_stock(c):
    from agent.analyst import is_paid, is_shipped, PREPAID
    orders = _rows(c, config.ORDER)
    dis = [o for o in orders if is_shipped(o) and not is_paid(o) and o.get("payment_method") in PREPAID]
    return "info", f"{len(dis)} prepaid orders shipped-while-unpaid (goal-2 signal)"


def monitor_new_entities(c):
    ents = sorted({t.get("name", "").split(".")[0] for t in c.list_tools() if "." in t.get("name", "")})
    RUNS.mkdir(exist_ok=True)
    seen_path = RUNS / "entities-seen.json"
    try:
        seen = set(json.loads(seen_path.read_text()))
    except Exception:
        seen = set()
    new = sorted(set(ents) - seen) if seen else []
    seen_path.write_text(json.dumps(sorted(set(ents) | seen)))
    if new:
        return "info", f"{len(ents)} entities — NEW since last run: {new} (probe these for fresh bugs)"
    return "info", f"{len(ents)} entities (none new since last run)"


CHECKS = [
    ("coupon_counter", check_coupon_counter),
    ("item_mrp", check_item_mrp),
    ("tenant_isolation", check_tenant_isolation),
    ("payment_stock", monitor_payment_stock),
    ("entities", monitor_new_entities),
]


def main():
    c = Client.login()
    results = []
    for name, fn in CHECKS:
        try:
            status, detail = fn(c)
        except Exception as e:
            status, detail = "error", f"{type(e).__name__}: {e}"
        results.append((name, status, detail))
        print(f"[{status.upper():6}] {name}: {detail}")

    date = datetime.date.today().isoformat()
    candidates = [(n, d) for n, s, d in results if s == "BUG"]
    newent = [d for n, s, d in results if n == "entities" and "NEW" in d]
    if candidates or newent:
        out = pathlib.Path("docs/bug-reports")
        out.mkdir(parents=True, exist_ok=True)
        f = out / f"{date}-daily-hunt.md"
        body = [f"# Daily hunt — {date} (team08 · Storefront)",
                "", "DRAFT — review and file via the bug button / API. Nothing was filed automatically.", ""]
        for n, d in candidates:
            body += [f"## candidate: {n}", "", d, ""]
        for d in newent:
            body += ["## new surface", "", d, ""]
        f.write_text("\n".join(body))
        print(f"\nDRAFTED {len(candidates)} candidate(s) + {len(newent)} new-surface note(s) -> {f}")
    else:
        print("\nNo new candidates. All monitored controls held; no new entities.")


if __name__ == "__main__":
    main()
