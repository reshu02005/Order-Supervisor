# Order Pilot

A workspace that watches an existing order from creation to delivery or cancellation. One Temporal workflow remembers each order, receives updates, wakes an assistant when useful, and waits between checks.

This is an order-supervision tool. It does not sell products. Sample orders and event buttons replace a real store/courier connection.

- [SETUP.md](SETUP.md): install and start the project.
- [DEMO.md](DEMO.md): a step-by-step walkthrough.
- [ARCHITECTURE.md](ARCHITECTURE.md): how the pieces fit together and current limits.
- [TECH_STACK_AND_DATA_FLOW.md](TECH_STACK_AND_DATA_FLOW.md): technology roles, database tables, and how the assistant reads and saves data.
- [VALIDATION.md](VALIDATION.md): checks actually performed.

## Workspace pages

The sidebar has **Orders**, **Assistants**, and **Integrations**. Each task opens on its own page; opening an order no longer adds its details below the order list.

| Page | Address | What to do there |
| --- | --- | --- |
| Orders | `/orders` | Search orders and filter active, review, or completed/stopped runs |
| New supervision | `/orders/new` | Choose an assistant and sample, then start a run |
| Order detail | `/orders/{id}` | Inspect the decision, Activity, Memory, Actions, and Final report |
| Assistants | `/assistants` | View saved assistant setups |
| New assistant | `/assistants/new` | Set instructions, tools, interval, and decision mode |
| Integrations | `/integrations` | Preview Shopify, WooCommerce, BigCommerce, and Etsy cards |

On order details, **Simulate event** and **Add instruction** open dialogs. **Check now**, **Pause/Resume**, and **Terminate supervision** control that run. Each order has a URL you can bookmark or reload.

Integration cards show **Coming soon** when opened. They do not request credentials, connect accounts, or import orders. Start with sample orders instead.

## Quick start

Install and open Docker Desktop, then open a terminal in this project folder:

```sh
docker compose up --build -d
```

Open [the dashboard](http://localhost:3000); it redirects to Orders. Use **Assistants → New assistant**, choose **Scripted demo**, and click **Create assistant**. Then use **Orders → New supervision**, select that assistant and a sample, keep **Create a fresh sample ID** checked, and click **Start supervision**. No API key is needed for this repeatable mode. For actual model decisions, follow the live-mode section of SETUP.md.

Required stack: Next.js App Router, Tailwind CSS, Python FastAPI, Temporal Python SDK, PostgreSQL. External tool effects are simulated records. The UI polls real persisted workflow results; it does not display prewritten scenario checkpoints.

This project is a local POC with no login. Service ports bind to localhost. Do not expose it as a public production service.

Screenshots: [Orders](docs/dashboard.jpg) · [Integrations](docs/integrations.jpg).
