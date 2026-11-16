# Validation results

Checks performed on 15 November 2026 using local Linux containers on an ARM64 development host. The images support AMD64 and ARM64. This does not certify a specific Windows laptop; use the prerequisites in SETUP.md.

| Check | Observed result |
| --- | --- |
| Frontend production build (`npm run build`) | Passed; Next.js 16.4.6 and TypeScript |
| Container build | Passed for frontend, API, and worker |
| Backend tests (`docker compose exec api python -m pytest tests -q`) | 7 passed |
| API integration (`python3 scripts/smoke.py`) | Passed against real PostgreSQL and Temporal |
| Worker restart | Same workflow resumed and processed a due timer; then completed |
| Browser walkthrough | Saved supervisor, started sample, sent delay, inspected saved actions, added contact restriction, paused/resumed run, and confirmed instruction in memory |

The integration check covered stable workflow identity, repeated start, routine signal without inference, actual durable timer, important update, pause, instruction, resume, all four simulated tool types, contact blocking, normal final report, rejection of events after completion, interrupt, and hard termination with partial report.

Backend tests also cover rolling memory compaction, tool allowlist enforcement, terminal report contents, decision schema validation, and the live HTTP adapter with a mocked response.

Tested runtime includes Python 3.12, Temporal Python SDK 1.20.0, Temporal CLI 1.10.1 / Server 1.32.2 / UI 2.56.4, PostgreSQL 17, and Node.js 22 in containers. The Temporal release manifest was checked for AMD64/ARM64 support. Frontend package versions are locked in package-lock.json; backend direct dependencies are pinned.

At a small demo workload, the five running containers used roughly 260–300 MiB combined in one observed snapshot. This excludes Docker Desktop/VM, operating system, browser, image storage, and the higher memory needed during builds. It is not a laptop minimum-RAM measurement.

Not verified: actual hosted-model connectivity (no token supplied), Windows/WSL execution, production-scale behavior, real courier/messaging integrations. Live mode never silently falls back to scripted decisions; a failed decision records a human-review fallback.

## Routed UI refresh — 15 November 2026

The frontend now has dedicated Orders, New supervision, Order detail, Assistants, New assistant, and Integrations routes. The root URL redirects to Orders.

Verified on the rebuilt local frontend:

- Production container build and TypeScript passed for all routes.
- Created an assistant, selected it on New supervision, and started a fresh real order workflow.
- Opened the order at its own URL and reloaded it successfully.
- Sent a delay through the event dialog and inspected saved tool results.
- Paused, added a contact-review instruction through its dialog, resumed, and read the instruction in Memory.
- Opened/cancelled the stop confirmation, immediately opened the event dialog, delivered the order, and read its complete final report.
- Order search and active/all filters returned the expected rows.
- All four local platform logos loaded. Shopify, WooCommerce, BigCommerce, and Etsy buttons each displayed the Coming soon message. Escape also closed the dialog.
- No browser console errors or warnings appeared in the final review.

Desktop screenshots: [Orders](docs/dashboard.jpg) and [Integrations](docs/integrations.jpg). Responsive CSS is included; this review did not include a separate narrow-screen browser test.

Integration cards are presentation-only. No OAuth, platform request, or store-data import is implemented. Logo sources and license are recorded in THIRD_PARTY_NOTICES.md.

## Documentation alignment

README, setup instructions, demo walkthrough, architecture, and the data-flow guide match the routed UI and its visible button/tab labels. Relative document/code/image links and the absence of personal absolute paths were checked. This documentation-only update did not rerun application tests; the observed results above are from the implementation and UI reviews.
