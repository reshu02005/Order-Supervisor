"""Small deterministic rules shared by the workflow and tests."""
TOOLS = ['send_customer_message', 'create_internal_note', 'escalate_issue', 'mark_order_for_review']
ROUTINE = {'payment_confirmed', 'shipment_created', 'order_created'}
TERMINAL = {'delivered', 'cancelled'}


def apply_event(s, event):
    kind = event['type']
    old = s['order_status']
    if kind == 'payment_confirmed' and old == 'created':
        s['order_status'] = 'paid'
    elif kind == 'shipment_created' and old in {'created', 'paid'}:
        s['order_status'] = 'shipped'
    elif kind == 'delivered':
        s['order_status'] = 'delivered'
        s['issues'] = []
    elif kind == 'order_cancelled':
        s['order_status'] = 'cancelled'
    elif kind in {'shipment_delayed', 'payment_failed', 'refund_requested'}:
        if kind not in s['issues']:
            s['issues'].append(kind)
    return kind not in ROUTINE


def memory(s):
    recent = [e['type'] for e in s['events'][-5:]]
    return (f"Order {s['order']['order_id']}: {s['order_status']}. "
            f"Issues: {', '.join(s['issues']) or 'none'}. "
            f"Instructions: {'; '.join(i['text'] for i in s['instructions']) or 'none'}. "
            f"Saved actions: {len(s['actions'])}. Recent updates: {', '.join(recent) or 'none'}. "
            f"{max(0, len(s['events'])-5)} older updates summarized; full timeline retained.")


def scripted(s):
    reason = f"Review triggered by {s['trigger']}."
    actions = []
    if s['trigger'] == 'start':
        actions = [{'tool': 'create_internal_note', 'text': 'Started watching the order.'}]
    elif s['issues']:
        reason += ' Unresolved issue: ' + ', '.join(s['issues']) + '.'
        actions = [{'tool': 'mark_order_for_review', 'text': reason},
                   {'tool': 'escalate_issue', 'text': reason}]
        if 'shipment_delayed' in s['issues']:
            actions.append({'tool': 'send_customer_message', 'text': 'Your parcel is delayed. We are checking with the courier.'})
    elif s['order_status'] in TERMINAL:
        reason = 'The order reached a terminal state. Write the final result.'
    else:
        actions = [{'tool': 'create_internal_note', 'text': 'Scheduled review: waiting for the next order update.'}]
    return {'reason': reason, 'actions': actions, 'next_wake_seconds': s['config']['wake_seconds']}


def validate_actions(s, proposal):
    allowed = s['config']['tools']
    blocked = s.get('contact_requires_review', False)
    result = []
    for a in proposal['actions'][:4]:
        status = 'succeeded'
        if a['tool'] not in allowed or (a['tool'] == 'send_customer_message' and blocked):
            status = 'blocked'
        if s['order_status'] in TERMINAL:
            status = 'blocked'
        result.append({**a, 'status': status, 'simulated': True})
    return result


def final_report(s, partial=False):
    good = [a for a in s['actions'] if a['status'] == 'succeeded']
    return {'outcome': 'terminated' if partial else s['order_status'],
            'completeness': 'partial' if partial else 'complete',
            'summary': f"Order {s['order']['order_id']} supervision {'stopped early' if partial else 'finished'}. Last order state: {s['order_status']}.",
            'important_actions': [a['text'] for a in good],
            'key_learnings': [f"Recorded {len(s['events'])} order updates and {s['decision_count']} decisions.",
                             'Routine updates were remembered without a new decision.'],
            'recommendations': ['Review unresolved issues with an operator.' if s['issues'] else 'No unresolved order issues remain.'],
            'unresolved_issues': s['issues']}
