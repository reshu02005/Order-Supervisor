import asyncio
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
with workflow.unsafe.imports_passed_through():
    from .domain import apply_event, memory, validate_actions, final_report, TERMINAL


@workflow.defn
class OrderSupervisor:
    def __init__(self):
        self.queue = []
        self.s = {}

    @workflow.signal
    def command(self, cmd: dict):
        self.queue.append(cmd)

    @workflow.query
    def state(self) -> dict:
        return self.s

    def log(self, kind, text):
        self.s['timeline'].append({'kind': kind, 'text': text, 'at': workflow.now().isoformat()})

    async def save(self):
        self.s['memory'] = memory(self.s)
        self.s['updated_at'] = workflow.now().isoformat()
        await workflow.execute_activity('save_state', self.s, start_to_close_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(maximum_attempts=3))

    @workflow.run
    async def run(self, initial: dict) -> dict:
        self.s = initial
        s = self.s
        pending = 'start'
        deadline = workflow.now()
        while True:
            while self.queue:
                c = self.queue.pop(0)
                op = c['op']
                if op == 'event':
                    e = c['event']
                    if e['event_id'] in s['seen_events']:
                        continue
                    s['seen_events'].append(e['event_id'])
                    s['events'].append(e)
                    important = apply_event(s, e)
                    self.log('event', e['type'] + ': ' + str(e.get('payload', {})))
                    if important:
                        pending = 'signal'
                elif op == 'instruction':
                    s['instructions'].append(c['instruction'])
                    s['contact_requires_review'] |= c['instruction'].get('contact_requires_review', False)
                    self.log('instruction', c['instruction']['text'])
                    pending = 'instruction'
                elif op == 'pause':
                    s['execution_status'] = 'paused'
                    self.log('control', 'Paused. New decisions/actions will wait.')
                elif op == 'resume':
                    s['execution_status'] = 'running'
                    pending = 'resume'
                    self.log('control', 'Resumed; reviewing accumulated updates.')
                elif op == 'interrupt':
                    pending = 'interrupt'
                    self.log('control', 'Immediate review requested.')
            if s['execution_status'] == 'paused':
                s['agent_state'] = 'idle'
                await self.save()
                await workflow.wait_condition(lambda: bool(self.queue))
                continue
            if pending or workflow.now() >= deadline:
                s['trigger'] = pending or 'timer'
                pending = None
                s['agent_state'] = 'thinking'
                await self.save()
                try:
                    proposal = await workflow.execute_activity('decide', s,
                        start_to_close_timeout=timedelta(seconds=40),
                        retry_policy=RetryPolicy(maximum_attempts=2))
                except Exception:
                    proposal = {'reason': 'Decision unavailable after bounded retries. Human review needed.',
                                'actions': [{'tool': 'mark_order_for_review', 'text': 'Model decision failed.'}],
                                'next_wake_seconds': s['config']['wake_seconds']}
                # Reconsider any signal received while inference was in flight.
                if self.queue:
                    pending = 'signal'
                    self.log('decision', 'Discarded stale proposal because new input arrived.')
                    continue
                s['decision_count'] += 1
                s['latest_decision'] = proposal['reason']
                self.log('decision', f"{s['trigger']}: {proposal['reason']}")
                for a in validate_actions(s, proposal):
                    a['receipt_id'] = f"action-{s['decision_count']}-{len(s['actions'])+1}"
                    a['at'] = workflow.now().isoformat()
                    # Avoid repeating the same simulated communication/escalation.
                    if a['tool'] != 'create_internal_note' and any(
                        old['tool'] == a['tool'] and old['text'] == a['text'] and old['status'] == 'succeeded'
                        for old in s['actions']):
                        continue
                    s['actions'].append(a)
                    if a['tool'] == 'mark_order_for_review' and a['status'] == 'succeeded':
                        s['needs_review'] = True
                    self.log('action', a['tool'] + ' / ' + a['status'] + ': ' + a['text'])
                if s['order_status'] in TERMINAL:
                    s['execution_status'] = 'completed'
                    s['agent_state'] = 'idle'
                    s['next_wake_at'] = None
                    s['final_report'] = final_report(s)
                    self.log('completed', 'Final report saved. Supervision finished.')
                    await self.save()
                    return s['final_report']
                deadline = workflow.now() + timedelta(seconds=proposal['next_wake_seconds'])
            s['agent_state'] = 'sleeping'
            s['next_wake_at'] = deadline.isoformat()
            await self.save()
            try:
                await workflow.wait_condition(lambda: bool(self.queue), timeout=max(timedelta(0), deadline-workflow.now()))
            except asyncio.TimeoutError:
                pass
