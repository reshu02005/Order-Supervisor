from copy import deepcopy
from app.domain import apply_event, memory, scripted, validate_actions, final_report, TOOLS
from app.activities import Decision, decide
import pytest


def state():
    return {'order':{'order_id':'TEST-1'}, 'order_status':'created','issues':[], 'events':[],
        'instructions':[], 'actions':[], 'config':{'tools':TOOLS,'wake_seconds':30,'mode':'scripted'},
        'trigger':'start','decision_count':1,'contact_requires_review':False}


def test_routine_and_important_events():
    s=state()
    assert not apply_event(s, {'type':'payment_confirmed'})
    assert s['order_status']=='paid'
    assert not apply_event(s, {'type':'shipment_created'})
    assert apply_event(s, {'type':'shipment_delayed'})
    assert 'shipment_delayed' in s['issues']
    apply_event(s, {'type':'payment_confirmed'})
    assert s['order_status']=='shipped'


def test_contact_and_allowlist_are_enforced():
    s=state();s['contact_requires_review']=True
    p={'actions':[{'tool':'send_customer_message','text':'Hello'},{'tool':'refund_money','text':'Refund'}]}
    assert all(a['status']=='blocked' for a in validate_actions(s,p))


def test_memory_compacts_but_history_is_retained():
    s=state();s['events']=[{'type':f'scan-{i}'} for i in range(30)]
    s['instructions']=[{'text':'Ask before messaging'}]
    m=memory(s)
    assert '25 older updates' in m and 'Ask before messaging' in m
    assert 'scan-29' in m and 'scan-0,' not in m
    assert len(s['events'])==30


def test_terminal_report_uses_saved_successes():
    s=state();s['order_status']='delivered'
    s['actions']=[{'text':'Saved note','status':'succeeded'}, {'text':'Blocked message','status':'blocked'}]
    r=final_report(s)
    assert r['important_actions']==['Saved note'] and r['completeness']=='complete'
    assert final_report(s,partial=True)['completeness']=='partial'


def test_scripted_output_matches_schema():
    s=state();s['issues']=['shipment_delayed']
    d=Decision.model_validate(scripted(s))
    assert d.next_wake_seconds==30
    assert len(d.actions)<=4


def test_invalid_model_output_cannot_dispatch():
    with pytest.raises(ValueError):
        Decision.model_validate({'reason':'bad','actions':[],'next_wake_seconds':0})


def test_live_adapter_with_mock_http(monkeypatch):
    s=state();s['config']['mode']='live';s['memory']='Paid'
    monkeypatch.setenv('LLM_API_KEY','test-token')
    monkeypatch.setenv('LLM_BASE_URL','https://example.com/v1')
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'choices':[{'message':{'content':'{"reason":"Wait for courier","actions":[],"next_wake_seconds":30}'}}]}
    def post(url,**kwargs):
        assert url=='https://example.com/v1/chat/completions'
        assert kwargs['headers']['Authorization']=='Bearer test-token'
        assert 'timeline' not in kwargs['json']['messages'][1]['content']
        return Response()
    monkeypatch.setattr('app.activities.httpx.post',post)
    assert decide(s)['reason']=='Wait for courier'
