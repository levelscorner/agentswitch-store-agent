# Bruno collection — team08 Storefront

Manual API client for poking the platform by hand (Bruno, the git-friendly Postman).

## Setup (one time)

1. Open Bruno → **Open Collection** → this `bruno/` folder.
2. Pick the **Suryodaya** environment (top-right). Set the secret var **password** to
   team08's password (Bruno stores secrets locally, never in the `.bru` files —
   `bruno/**/.env` is gitignored).
3. Run **01 Login** — it captures `token` into the environment automatically.
4. Every other request uses `{{token}}`. Run **02 Who am I** to confirm the seat, then
   **03 tools/list** to see the real Storefront entity names (Coupon/Order/Payment/stock).

Switch to **Keystone** to test the US instance (`{{ASUSA}}`) — swap `ASIND`→`ASUSA` in a
request's URL, or edit the environment.

## Requests

| # | Request | What |
|---|---|---|
| 01 | Login | POST /api/auth/login → captures token |
| 02 | Who am I | GET /api/auth/me → seat, roles, allowed_apps |
| 03 | tools/list | the seat's real MCP tools + entity names |
| 04 | Storefront orders | GET /api/storefront/account/orders |
| 05 | Storefront products | GET /api/storefront/products |
| 06 | MCP entity list | tools/call template — confirm the entity name from 03 first |
| 09 | File a bug | POST /api/bug-report (fill the description) |
