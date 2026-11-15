"""Real API/Temporal/PostgreSQL smoke test. Start Compose first. No extra packages."""
import json
import time
import urllib.request
import urllib.error
import uuid
import os
BASE=os.getenv('API_URL','http://localhost:8000')


def call(path, body=None):
    req=urllib.request.Request(BASE+path, data=json.dumps(body).encode() if body is not None else None,
                               headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as r:
        return json.load(r)


def wait(id, predicate, timeout=45):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        s=call('/api/runs/'+id)
        if predicate(s):return s
        time.sleep(.2)
    raise AssertionError('Timed out waiting for run state: '+json.dumps(s))


def main():
    cfg=call('/api/supervisors',{'name':'Smoke test assistant','base_instruction':'Watch the order.','wake_seconds':8,'mode':'scripted'})
    id='TEST-'+uuid.uuid4().hex[:8]
    body={'supervisor_id':cfg['id'],'order':{'order_id':id,'customer_name':'Sample Customer','item':'Backpack','amount_minor':249900}}
    call('/api/runs',body)
    s=wait(id,lambda s:s['decision_count']==1 and s['agent_state']=='sleeping')
    assert s['actions'][0]['tool']=='create_internal_note'
    call('/api/runs',body)
    assert len([r for r in call('/api/runs') if r['id']==id])==1
    call(f'/api/runs/{id}/events',{'type':'payment_confirmed'})
    s=wait(id,lambda s:s['order_status']=='paid')
    assert s['decision_count']==1, 'Routine payment should not invoke main agent'
    wait(id,lambda s:s['decision_count']>=2)
    assert any(x['text'].startswith('timer:') for x in call('/api/runs/'+id)['timeline'])
    call(f'/api/runs/{id}/pause',{})
    s=wait(id,lambda s:s['execution_status']=='paused')
    count=s['decision_count']
    call(f'/api/runs/{id}/instructions',{'text':'Ask before contacting customer.','contact_requires_review':True})
    call(f'/api/runs/{id}/events',{'event_id':'delay-1','type':'shipment_delayed','payload':{'reason':'Sorting backlog'}})
    s=wait(id,lambda s:len(s['events'])==2 and len(s['instructions'])==1)
    assert s['decision_count']==count
    call(f'/api/runs/{id}/resume',{})
    s=wait(id,lambda s:s['decision_count']>count and s['agent_state']=='sleeping')
    assert any(a['tool']=='send_customer_message' and a['status']=='blocked' for a in s['actions'])
    assert any(a['tool']=='escalate_issue' and a['status']=='succeeded' for a in s['actions'])
    assert s['needs_review']
    call(f'/api/runs/{id}/events',{'event_id':'delay-1','type':'shipment_delayed'})
    call(f'/api/runs/{id}/events',{'type':'delivered'})
    s=wait(id,lambda s:s['execution_status']=='completed')
    assert s['final_report']['completeness']=='complete' and s['next_wake_at'] is None
    call('/api/runs',body)
    assert call('/api/runs/'+id)['execution_status']=='completed'
    try:
        call(f'/api/runs/{id}/events',{'type':'shipment_delayed'})
        raise AssertionError('Ended run should reject new events')
    except urllib.error.HTTPError as e:assert e.code==409
    other=id+'-stop';body['order']['order_id']=other
    call('/api/runs',body)
    wait(other,lambda s:s['decision_count']==1)
    call(f'/api/runs/{other}/interrupt',{})
    wait(other,lambda s:s['decision_count']>=2)
    call(f'/api/runs/{other}/terminate',{})
    s=call('/api/runs/'+other)
    assert s['execution_status']=='terminated' and s['final_report']['completeness']=='partial'
    print('PASS: real workflow start/uniqueness, routine signal, durable timer, pause, instruction, important signal, resume, tools/contact guard, completion, interrupt, hard termination.')
    print('Runs:',id,other,'(retained for inspection in the dashboard and Temporal)')

if __name__=='__main__':main()
