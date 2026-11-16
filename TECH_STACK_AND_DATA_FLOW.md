# How the technology and data flow work

Follow one example: a sample customer ordered a backpack. We load that order, receive a courier delay, and show what the assistant decided.

## 1. Each technology has one job

| Technology | Job in this project | Example |
| --- | --- | --- |
| Next.js App Router and React | Show the dashboard and handle button clicks | Display an order and send a delay update |
| Tailwind CSS and CSS | Style the screens | Cards, buttons, spacing, responsive layout |
| Python FastAPI | Receive screen requests and validate their data | Accept an order or an event |
| Temporal service | Remember workflow progress, signals, and scheduled checks | Remember that this order needs another check |
| Temporal Python worker | Execute the workflow and its activities | Review an event and request a decision |
| LLM through HTTPX | Suggest a decision in Live mode | Suggest a customer update after a delay |
| Pydantic | Check request and model-response structure | Reject an invalid check interval |
| PostgreSQL through Psycopg | Save the records displayed on screen | Save history, actions, memory, and result |
| Docker Compose | Start and connect the services | Run frontend, API, worker, Temporal, and database |

The assistant is Python code running in the worker. The LLM suggests what to do; it does not connect to PostgreSQL or write SQL. Our application checks the suggestion and saves the resulting records.

## 2. There are only two application tables

Both tables have the same simple structure:

```sql
id   TEXT PRIMARY KEY
data JSONB NOT NULL
```

`id` uniquely identifies a row. `JSONB` stores a structured object with named fields and lists. This keeps the small POC simple.

| Table | One row represents | What its `data` contains |
| --- | --- | --- |
| `supervisors` | One assistant setup | Name, base instruction, allowed tools, check interval, Scripted/Live mode |
| `runs` | One supervised order | Order details, copied settings, current state, events, timeline, actions, memory, instructions, next check, final report |

There are **no separate tables for messages, events, memory, or actions** in this implementation. Those are fields inside a `runs.data` object.

### Example supervisor row

```json
{
  "id": "example-supervisor-id",
  "data": {
    "id": "example-supervisor-id",
    "name": "Delivery assistant",
    "base_instruction": "Watch the order and help when delayed.",
    "tools": ["send_customer_message", "create_internal_note", "escalate_issue", "mark_order_for_review"],
    "wake_seconds": 20,
    "mode": "scripted"
  }
}
```

The API generates the real supervisor ID. Each order copies these settings into `runs.data.config`, so changing which setup you choose for a new order does not change existing runs.

### Important fields inside a run

| Field in `runs.data` | Meaning |
| --- | --- |
| `order` | Customer, product, order ID, amount, currency |
| `config` | Copied supervisor settings |
| `workflow_id` | Temporal identity, such as `order-supervisor:DEMO-1001` |
| `order_status` | Business state: created, paid, shipped, delivered, cancelled |
| `execution_status` | Supervisor state: running, paused, completed, terminated |
| `agent_state` | Whether it is idle, thinking, or sleeping |
| `events` | Received order updates |
| `timeline` | Human-readable history of events, decisions, controls, and actions |
| `actions` | Simulated tool results, including succeeded or blocked status |
| `instructions` | Operator instructions added after starting |
| `memory` | Short notebook for the next decision |
| `latest_decision`, `decision_count` | Most recent explanation and number of accepted decisions |
| `next_wake_at` | Next scheduled check |
| `issues`, `needs_review` | Unresolved problems and human-review flag |
| `final_report` | Summary, actions, learnings, recommendations, unresolved issues |

For example, a saved action inside `actions` looks like this. Other fields in the run are omitted:

```json
{
  "tool": "send_customer_message",
  "text": "Your parcel is delayed. We are checking with the courier.",
  "status": "succeeded",
  "simulated": true,
  "receipt_id": "action-2-3",
  "at": "2026-11-15T09:15:00+00:00"
}
```

“Succeeded” here means the simulated action record was saved. No real message was delivered.

## 3. Starting an order

1. **Load samples:** open Orders → New supervision. The shared workspace calls `GET /api/samples`. FastAPI reads [orders.json](backend/fixtures/orders.json). Sample orders are initially in this file, not in PostgreSQL.
2. **Save setup:** Assistants → New assistant calls `POST /api/supervisors`. FastAPI inserts a row into `supervisors`.
3. **Start supervision:** the screen sends the selected order and supervisor ID to `POST /api/runs`.
4. **Read settings:** FastAPI fetches the selected `supervisors` row.
5. **Save initial order:** FastAPI inserts the starting snapshot into `runs`. In this POC, the row ID is the order ID, for example `DEMO-1001`.
6. **Start workflow:** FastAPI gives that snapshot to the Temporal workflow with ID `order-supervisor:DEMO-1001`.
7. **First decision:** the worker runs the decision activity, records the result, and saves the updated snapshot through `save_state`.

The setup must exist before you click Start supervision. New supervision defaults to a fresh sample ID so repeated demos keep earlier records. If the same order ID is submitted again, its existing database row is not overwritten and a second workflow is not started.

## 4. A delay arrives: think, act, save

```text
Order detail → Simulate event dialog → Send event
        ↓
FastAPI reads the run to find its workflow ID
        ↓
Temporal receives the event as a signal
        ↓
Worker updates the order's current working state
        ↓
Decision activity receives the current context
        ↓
Application validates proposed actions and records their results
        ↓
save_state activity writes the updated run into PostgreSQL
        ↓
Dashboard fetches that saved run and displays the changes
```

The Simulate event dialog closes when its request is accepted. An event request being accepted does not mean its decision has finished. The API returns `202 Accepted`; the worker processes it afterward.

### What does the decision activity read?

It receives the current workflow state as an argument. It does **not** fetch the order from PostgreSQL on every wake-up.

In Live mode, it sends these fields to the model: order, order status, issues, short memory, instructions, trigger, supervisor settings, and the last five events. The token comes from `LLM_API_KEY` on the server and is used in the HTTP authorization header. It is not stored in either application table.

In Scripted mode, Python rules return an example decision without a model request.

### What gets written?

The workflow updates its `latest_decision`, `actions`, `timeline`, memory, and next check. The four simulated tools are records created by application code; their effects are persisted together by the `save_state` activity.

`save_state` performs an **upsert**: insert the run if absent; otherwise replace its saved `data` with the latest snapshot. This is not a new row for every event. It uses a transaction and row lock, and refuses to overwrite a run already marked terminated.

## 5. Fetching data back to the screen

The dashboard refreshes every two seconds using:

| Request | Data source |
| --- | --- |
| `GET /api/runs` | All saved rows in `runs` |
| `GET /api/supervisors` | Saved rows in `supervisors` |
| `GET /api/samples` | The sample JSON file |

The shared workspace provider loads the saved data; changing pages or polling the API does not itself call the LLM. The Orders page lists runs; opening an order navigates to `/orders/{id}`, where its detail page selects that order from the returned run list. The latest decision card uses `latest_decision`; the Activity, Memory, Actions, and Final report panels use the corresponding fields in that same saved run.

`GET /api/runs/{id}` also exists for fetching one run, and is used by the smoke test. The current dashboard uses the run-list response for its detail view.

### What happens on Integrations?

The Shopify, WooCommerce, BigCommerce, and Etsy card descriptions are defined in the frontend. Their SVG logos are served from `frontend/public/integrations/`.

Clicking **View integration** sets local screen state and opens a **Coming soon** dialog. Closing it clears that state. No integration record is written to `supervisors` or `runs`, and there is no separate integrations table. The shared provider still performs its ordinary read-only workspace polling.

## 6. PostgreSQL and Temporal remember different things

| Store | What it remembers |
| --- | --- |
| PostgreSQL | Application records that the dashboard reads |
| Temporal's own storage | Workflow execution history, signals, activity results, and timers |

In this local Compose setup, Temporal uses its own SQLite file in the `temporal-data` volume. It does **not** store its internal history in the application's PostgreSQL tables. PostgreSQL has its own `postgres-data` volume.

If the worker restarts, Temporal rebuilds its working state from recorded workflow history. Recovery does not consist of loading the `runs` row and starting a new workflow. The persisted run is the dashboard's saved view; Temporal controls execution.

## 7. Instructions, memory, and finishing

- **New instruction:** sent as a signal, added to workflow state, then saved in `runs.data.instructions`. The contact-review checkbox sets a constraint enforced by application code.
- **Short memory:** generated by the Python `memory()` function from current facts and five recent events. It is not a separate vector database or an LLM-written summary. Full event/timeline lists remain saved.
- **Delivery/cancellation:** the workflow builds `final_report` from its facts and saved successful actions, saves it, then finishes. Report generation is deterministic Python code, even in Live mode.
- **Terminate:** FastAPI hard-stops the workflow, then updates `runs` directly to save a partial report. The stopped workflow cannot save its own cleanup result.

## 8. Where to look in the code

| File | Relevant responsibility |
| --- | --- |
| [workspace.tsx](frontend/components/workspace.tsx) | Shared navigation, data loading, and two-second refresh |
| [orders/page.tsx](<frontend/app/(workspace)/orders/page.tsx>) | Order list, search, filters, and links to detail pages |
| [Order detail](<frontend/app/(workspace)/orders/[id]/page.tsx>) | Decisions, activity tabs, update/instruction dialogs, controls |
| [New assistant](<frontend/app/(workspace)/assistants/new/page.tsx>) | Setup form and supervisor creation request |
| [New supervision](<frontend/app/(workspace)/orders/new/page.tsx>) | Assistant/sample selection and start request |
| [Integrations](<frontend/app/(workspace)/integrations/page.tsx>) | Local platform cards and Coming soon dialog |
| [api.ts](frontend/lib/api.ts) | Browser-to-FastAPI requests |
| [main.py](backend/app/main.py) | API routes, initial inserts, reads, termination write |
| [db.py](backend/app/db.py) | Table creation, connections, SQL helpers |
| [workflows.py](backend/app/workflows.py) | Working state, signals, waiting, decisions, action records |
| [activities.py](backend/app/activities.py) | Model request and `save_state` database write |
| [domain.py](backend/app/domain.py) | Event rules, action validation, memory, final report |
| [compose.yaml](compose.yaml) | Services, database connection, persistent volumes |

To inspect saved order status without installing a database client:

```sh
docker compose exec db psql -U supervisor -d supervisor -c "SELECT id, data->>'order_status' AS order_status FROM runs;"
```

To inspect actions for the backpack sample:

```sh
docker compose exec db psql -U supervisor -d supervisor -c "SELECT jsonb_pretty(data->'actions') FROM runs WHERE id='DEMO-1001';"
```

This two-table snapshot design is sufficient for the small demo. It rewrites growing history lists, so it is not intended as a large-scale database design.
