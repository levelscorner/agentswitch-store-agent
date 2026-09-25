# Gap Report — Seat 8 · Storefront vs **Shopify**

**Team 08 · Week 1 deliverable (Section 8, step 3).** One page, three questions, specifics.

**The product, and why.** Shopify is the Rillet of storefront: an AI-native commerce
platform that shipped the thing this seat is being asked to build, in public. It runs
**five official MCP servers** (Storefront, Catalog, Customer Account, Checkout, Dev), a
**Universal Commerce Protocol** co-developed with Google (Jan 2026) so a shopper's own
agent can discover → cart → checkout across stores, and **Sidekick**, an in-admin agent
that writes payments/fulfillment queries and creates discounts from plain English. The
bar is visible and documented.

**What our seat is.** The `/api/storefront/*` surface — `products`, `categories`,
`checkout`, `order`, `payment/verify`, `stock-alerts/{queue,run}`, `shipping-methods` —
plus entities `Coupon`, `CouponLedger`, `Order`, `Payment`, stock. CRUD + module
endpoints over one D2C line. No agent layer, no shopper-facing protocol, no analytics DSL.

## 1 · What they do that we do not

- **Shopper-facing agentic checkout.** Storefront MCP + UCP let an external buying agent
  browse a store's catalog, build a cart, and check out. We have `POST /checkout`, but no
  MCP/protocol an outside agent can drive.
- **Cross-store product discovery.** Catalog MCP exposes products to shopping agents
  across merchants. Our catalog is a single-seat CRUD list.
- **Plain-language merchant ops (Sidekick).** "20% off code WELCOME20, first-time
  customers, one use, expires in 30 days" → created in ~5s; it segments customers and
  writes payouts/fulfillment queries. We expose raw `Coupon.create`; no assistant, no NL.
- **A native analytics/query layer (ShopifyQL).** Coupon performance and payment/payout
  reporting are first-class queries. We have generic `report`/`financial_report`, but no
  coupon-performance or payment↔stock view.
- **Payment↔stock kept consistent by the platform.** Shopify Payments decrements
  inventory on a paid order as a system invariant. Our seat's own graded question assumes
  the two *can* disagree — i.e. that reconciliation is not enforced. That is the gap.

## 2 · Which gaps an agent closes today (ours) vs need platform work (theirs)

**Ours — orchestration over the API we already have:**
- **Coupon performance** (`coupon_ledger_ties`): walk `CouponLedger` + `Order`, compute
  redemptions, revenue and discount for the launch coupon, and check usage ties to the
  ledger. No new tables — an agent assembles it today.
- **Payment/stock disagreement** (`payment_stock_agree`): join `Payment` + stock + `Order`,
  list rows paid-but-not-decremented (or moved-but-unpaid). Pure orchestration.
- **Sidekick-style discount creation:** map NL → `Coupon.create` with limits/expiry.

**Theirs — needs new tables/endpoints, so it is a platform bug/feature to report:**
- A shopper-facing MCP / agentic-checkout protocol (UCP-equivalent).
- Payment↔stock reconciliation as an enforced invariant, not a mismatch an agent finds
  after the fact.
- A queryable analytics layer (ShopifyQL-equivalent) instead of ad-hoc reads.

## 3 · What an agent can do that their UI cannot

Shopify's UI (and even Sidekick, scoped to one admin action) still makes a **human drive
each step**. Our agent holds the whole Section-8 request as one goal — *"how did the launch
coupon perform, and find any order where payment and stock disagree"* — across many steps,
re-reading state that other teams change underneath it: pull the coupon's ledger, compute
its performance, then switch task and reconcile payments against stock, trace each
disagreement to its order, classify it (refund-not-restocked vs oversell), and report what
to fix — in one pass, with the correct answer being *refusal* when the data cannot support
a claim. Nobody clicks through a discount report, an inventory screen, and an order audit
separately.

---
*Sources:* [Shopify Storefront MCP docs](https://shopify.dev/docs/apps/build/storefront-mcp/servers/storefront) · [Shopify Spring '26: Agentic Commerce (UCP + Catalog)](https://www.digitalapplied.com/blog/shopify-spring-2026-edition-agentic-commerce-ucp-catalog) · [Sidekick features 2026](https://wearepresta.com/shopify-sidekick-features-2026-the-merchants-guide-to-agentic-commerce/) · [6 best MCP servers for ecommerce 2026](https://checkoutpage.com/blog/best-mcp-servers-for-ecommerce)
