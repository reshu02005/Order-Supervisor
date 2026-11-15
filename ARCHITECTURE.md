# Architecture

For a beginner walkthrough of the tables, reads, writes, and one delay event, see [the technology and data-flow guide](TECH_STACK_AND_DATA_FLOW.md).

```text
Next.js/Tailwind dashboard → FastAPI → Temporal signals
                                         ↓
                                  Python worker
                                  order workflow
                                         ↓
                         model decision / save-state activities
                                         ↓
                                    PostgreSQL
                                         ↓
                              dashboard polls snapshots
```

## Frontend pages and navigation

Next.js App Router serves Orders (`/orders`), New supervision (`/orders/new`), Order detail (`/orders/{id}`), Assistants (`/assistants`), New assistant (`/assistants/new`), and Integrations (`/integrations`). The root redirects to Orders.

The shared [workspace component](frontend/components/workspace.tsx) supplies the sidebar and polls the API every two seconds. Route changes select a different screen; they do not start another workflow. The order-detail page uses dialogs for events, instructions, and termination confirmation, plus Activity/Memory/Actions/Final report tabs.

Integration cards use local SVG assets and a local Coming soon dialog. There is no integration endpoint or connection table. Normal workspace polling continues, but opening a card does not initiate an account connection or import. Asset sources are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Workflow and persistence

Each order has a stable `order-supervisor:{order_id}` workflow ID. The API stores a starting snapshot, starts the workflow, and returns the existing order for repeated starts. Completed workflow IDs cannot be reused.

Workflow signal handlers only enqueue commands. One main loop applies events and controls, records history, and decides whether the assistant should wake. Payment and shipment creation are routine; other events wake the main agent. An absolute durable deadline survives routine updates. Paused workflows record incoming facts and wait for resume. New input received during a model call makes its proposal stale and causes another review before dispatch.

Model calls and PostgreSQL I/O execute as activities. In Scripted mode, a deterministic adapter chooses the example actions. Live mode requests validated JSON from the configured model endpoint. Four simulated tools produce action records: customer message, internal note, escalation, and human-review flag. Allowlist and contact-constraint checks apply to both modes. Successful/blocked effects and their receipts are committed together in the saved snapshot, so a persistence retry does not create another effect row.

Two small PostgreSQL tables store supervisor settings and run snapshots as JSONB. Schema creation is idempotent at startup. Each run contains order facts, raw event/timeline history, instructions, tool results, current status, next wake time, compact memory, and final output. Memory keeps current facts plus five recent events; older events remain in history. This compacts model input, not Temporal event history.

Final reports are generated deterministically from saved facts/results. Delivery/cancellation causes finalization inside the workflow. Hard termination uses Temporal's client API; the backend then records a partial report from persisted records. A row lock and terminal-state guard prevent a late snapshot write from overwriting a terminated run.

## Limits and deliberate choices

- This is a local proof of concept, with no authentication or real platform integrations.
- All four tool effects are simulated records persisted by the save-state activity. A real external provider would need its own idempotency and delivery reconciliation.
- Instructions in free text guide Live mode; the checkbox is the hard customer-contact restriction. Scripted mode demonstrates predefined rules.
- Workflow command order is arrival order; there is no full external-event ordering/reconciliation subsystem. Duplicate event IDs are ignored within a run.
- An API/Temporal handoff is not one atomic transaction. Retrying an order start with the same ID repairs a failed start; durable signal redelivery is future scope.
- A running activity may finish after pause or termination is requested. Partial reports contain only already persisted results.
- Raw histories grow; Continue-As-New, pagination, production migrations, and load testing are future scope. The POC targets a few demo orders.
- PostgreSQL and Temporal use persistent named volumes. Temporal's embedded development server is appropriate for this local demo, not production hosting.

References: [Temporal Python SDK](https://github.com/temporalio/sdk-python), [Temporal CLI](https://github.com/temporalio/cli), [model endpoint reference](https://developers.openai.com/api/reference/resources/chat).
