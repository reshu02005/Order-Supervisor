# Walkthrough: supervise one sample order

Allow about 7–9 minutes. Follow [SETUP.md](SETUP.md), then open [Orders](http://localhost:3000/orders) and [Temporal history](http://localhost:8233). Use the sidebar to move between Orders, Assistants, and Integrations.

## 1. Explain the project

“This dashboard watches existing orders. A sample order stands in for an order arriving from a shopping website. The assistant remembers updates, acts when needed, and checks again later. External messages and escalations are simulated.”

Choose **Scripted demo** for a repeatable walkthrough. To demonstrate real AI, set the environment variables first and choose **Live AI**; wording and tool choices may vary. State the mode clearly.

## 2. Configure the assistant

Open **Assistants → New assistant**. Keep all four tools checked. Name it “Delivery assistant.” Use:

> Watch this order. If a shipment is delayed, save a customer update and ask operations for help. Keep the next check at 20 seconds.

Set check interval to **20 seconds**, choose Scripted demo, and click **Create assistant**. Scripted decisions use fixed example rules, not arbitrary prose instructions.

## 3. Start an order

Open **Orders → New supervision**. Choose the assistant and backpack sample. Keep **Create a fresh sample ID** checked, then click **Start supervision**. Its dedicated order-detail page opens at `/orders/{id}`. Refresh once to show that the URL still opens the same order. The order is also listed on Orders; **Back to orders** returns to the list.

Show on the order-detail page:

- Latest assistant decision and mode.
- Decision count: initially 1.
- The first saved internal note under Actions.
- The next check time.
- The matching `order-supervisor:...` workflow in Temporal.

This is a real workflow, not a sequence of prepared screens.

## 4. Send routine updates

In Order overview, click **Simulate event**. In its dialog, set **Event type** to **payment confirmed**, optionally add Details, and click **Send event**. The dialog closes when the request is accepted; wait for the saved update in the **Activity** tab. Open Simulate event again and repeat with **shipment created**. Order status changes while the assistant can remain asleep. If twenty seconds passes, a timer decision may also happen; distinguish that from the routine event.

## 5. Send a delay

Open **Simulate event**, choose **shipment delayed**, enter “Courier reports a sorting backlog” under Details, and click **Send event**. Wait for a signal-triggered decision. In Scripted mode, Actions shows a simulated customer message, escalation, and review flag. No real message is sent.

Open Memory to see the short notebook. Show the received signal in Temporal history.

## 6. Show the scheduled check

Send no more events. Wait at least twenty seconds. The decision count increases and Activity contains a **timer** decision. Explain: “The assistant can wake even when the courier sends nothing.”

## 7. Add an instruction to the live run

Here “live run” means an already running workflow, including one using Scripted mode.

Press Pause and wait until the run displays **paused**. Click **Add instruction** to open its dialog and enter:

> Ask for human review before contacting the customer.

Tick **Customer contact requires human review** and click Add instruction. Open **Simulate event** again and send another shipment delayed update while paused. It is remembered, but no new decision starts.

Press Resume. Show the instruction in Memory and a **blocked** simulated customer-message proposal in Actions. Earlier successful messages remain in history; the new restriction does not undo them.

## 8. Complete the order

Open **Simulate event** and send **delivered**. Wait for **completed**. Open Final report and show the summary, important actions, learnings, and recommendations. The next scheduled check is cleared. The workflow completes in Temporal too.

## 9. Demonstrate stopping separately

Start another order through New supervision, keeping the fresh sample ID option checked. Wait for its first decision. Click Check now and show the new review. Click **Terminate supervision**, then confirm **Terminate run**. Final report is marked **partial**; the order is not falsely described as delivered. This run cannot resume.

## 10. Preview planned integrations

Open **Integrations** in the sidebar. Shopify, WooCommerce, BigCommerce, and Etsy have locally bundled logo cards labeled **Coming soon**. Click **View integration** on one card, read the message, and close it with **Got it**, the close button, or Escape. No credentials are requested and no store is connected. Use **Start a sample order** to return to New supervision.

Before closing, return to Orders and demonstrate Search orders and the Active / Needs review / Completed / stopped filters.

## 11. Close with one learning and one limitation

“Routine updates can be remembered without spending an AI call every time. The current tools save simulated effects; connecting a real store or messenger is future scope.”

Record this walkthrough on the working application. Do not display tokens, shell environment values, personal file locations, or unrelated desktop information in the video.
