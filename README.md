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

## Architecture — a small hierarchy (shared with the Website seat)

A **supervisor** routes the planned goals to a roster; each graded goal is a **sub-agent**
(a subgraph) that gets only a scoped slice of state, runs its own internal DAG, and returns
only its declared outputs — its scratch never leaks back. Hand-rolled on our own DAG.

```
respond()
  → plan (LLM → goals)
  → Supervisor routes the roster (independents run in parallel):
       coupon_ledger  (subgraph)  fetch coupons ‖ orders → reconcile → assemble
       payment_stock  (subgraph)  fetch orders → detect → assemble
       refuse         (function)  refuse exact per-order profit (no cost-of-goods data)
  → verify (re-read the DB — truth, not the agent's words)
  → compose
```

Domain-agnostic backbone (identical to the Website seat):
- `agent/supervisor.py` — routes goals to workers, then verify. `agent/subgraph.py` — the sub-agent primitive.
- `agent/state.py` — typed blackboard: channels + reducers + `scope()`/`absorb()`.
- `agent/dag.py` — the engine (topological run, parallel independents, per-node timing trace). `agent/memory.py` — 3-tier memory (S07).
- `agent/llm.py` — model routing. `agent/reliability.py` — retries, JSON repair, budget/circuit breaker (S12). `agent/verify.py` — reality-check verifier (S17).

Storefront-specific:
- `agent/config.py` — seat + entity names (`Coupon`, `WebOrder`, launch coupon).
- `agent/subgraphs.py` — the `coupon_ledger` and `payment_stock` sub-agents.
- `agent/analyst.py` — goal wrappers (route through the subgraphs) + the refusal.
- `harness/` — scored task runner · `adapter.py` seam · `daily_hunt.py` (read-only probe-and-draft).

## Status

- [x] Agent live — both goals + refusal, harness **4/4**, verified against the DB.
- [x] Hierarchy: supervisor + subgraph sub-agents + typed state/reducers + observability trace.
- [x] Gap report (vs Shopify) + bugs/enhancements filed; daily probe-and-draft hunt in place.

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
