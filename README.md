# AgentSwitch — Store Agent (Seat 8 · team08)

The **Storefront** seat: the D2C line end to end — web orders, catalogue, checkout,
coupons, and where **payment and stock disagree**.

Sibling repo: the Website seat lives in `agentswitch-web-agent`. Same agent backbone,
different domain.

## The bar (Section 8 request)

> "How did the launch coupon perform, and find any order where payment and stock disagree."

Two graded goals, judged by the seat's predicate **against the database**, not by how
the reply reads:

| Goal id | Question |
|---|---|
| `storefront.coupon_ledger_ties` | How did the launch coupon do — does usage tie to the ledger? |
| `storefront.payment_stock_agree` | Where do payment and stock disagree? |

## Week-1 deliverable — the gap report (Section 8, step 3)

One page. Step 2 (the skipped one): find the best real product in this domain, then
write the gap between it and this seat. Worked example in the brief: Ledger vs **Rillet**
(ships an MCP server over its own ledger). Draft: `docs/gap-report.md`.

## Architecture (shared with the Website seat)

Domain-agnostic backbone, copied verbatim:
- `agent/client.py` — MCP client (login → Bearer → tools/call; errors ride inside HTTP 200).
- `agent/llm.py` — Anthropic call + model routing (Haiku/Opus). `agent/reliability.py` — retries, JSON repair, budget/circuit breaker.
- `agent/dag.py` — parallel goal nodes on a shared blackboard (S08). `agent/memory.py` — 3-tier memory on `AgentMemory` (S07).
- `agent/verify.py` — reality-check verifier (S17). `harness/` — scored task runner + `adapter.py` integration seam.

Storefront-specific:
- `agent/config.py` — seat + entity names (**confirm against `tools/list` on first login**).
- `agent/analyst.py` — the two goal runners (probe live, then reconcile).
- `agent/respond.py` — planner + DAG wiring for the two goals.

## Status

- [x] Backbone in place; harness structure mirrors the Website seat.
- [ ] **Login once** to confirm real entity/field names, then wire the two runners (marked `TODO(after login)`).
- [ ] Week-1 gap report.

## Run

```bash
# 1. put the real password in .env.team08 (gitignored)
set -a; source .env.team08; set +a

python3 -m agent.client          # discover the seat: roles, allowed_apps, tool count
python3 -m harness.run           # scored task table (seat_access passes at login)
python3 -m agent.respond "How did the launch coupon perform, and where do payment and stock disagree?"
```

**Change rules:** agent code is ours; the harness/predicates/schemas are ask-first (report as a
bug with a reproducing case); never touch another team's agent or the shared data to force a pass.
