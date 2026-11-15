import asyncio
import json
import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.common import WorkflowIDReusePolicy
from . import db
from .domain import TOOLS, final_report


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    for attempt in range(30):
        try:
            app.state.temporal = await Client.connect(os.getenv('TEMPORAL_ADDRESS', 'localhost:7233'))
            break
        except Exception:
            if attempt == 29:
                raise
            await asyncio.sleep(1)
    yield


app = FastAPI(title='Order Supervisor', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000','http://127.0.0.1:3000'],
                   allow_methods=['*'], allow_headers=['*'])


class Supervisor(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_instruction: str = Field(min_length=1, max_length=2000)
    tools: list[Literal['send_customer_message','create_internal_note','escalate_issue','mark_order_for_review']] = Field(default_factory=lambda: TOOLS.copy())
    wake_seconds: int = Field(default=30, ge=5, le=86400)
    mode: Literal['scripted','live'] = 'scripted'


class Order(BaseModel):
    order_id: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    customer_name: str = Field(min_length=1, max_length=100)
    item: str = Field(min_length=1, max_length=200)
    amount_minor: int = Field(ge=0)
    currency: str = 'INR'


class Start(BaseModel):
    supervisor_id: str
    order: Order


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = Field(min_length=1, max_length=80)
    payload: dict = Field(default_factory=dict)


class Instruction(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    contact_requires_review: bool = False


def find(id):
    s = db.get('runs', id)
    if not s:
        raise HTTPException(404, 'Order run not found')
    return s


@app.get('/health')
async def health():
    try:
        db.list_rows('supervisors')
        await app.state.temporal.service_client.check_health()
        return {'status': 'ok', 'database': 'connected', 'temporal': 'connected'}
    except Exception:
        raise HTTPException(503, 'A dependency is unavailable')


@app.post('/api/supervisors', status_code=201)
def config(body: Supervisor):
    if body.mode == 'live' and not os.getenv('LLM_API_KEY'):
        raise HTTPException(422, 'Set LLM_API_KEY on the backend and worker before choosing live mode.')
    data = {'id': str(uuid.uuid4()), **body.model_dump()}
    db.put('supervisors', data['id'], data)
    return data


@app.get('/api/supervisors')
def configs():
    return db.list_rows('supervisors')


@app.get('/api/supervisors/{id}')
def get_config(id: str):
    data = db.get('supervisors', id)
    if not data:
        raise HTTPException(404, 'Supervisor not found')
    return data


@app.get('/api/samples')
def samples():
    return json.loads((Path(__file__).parents[1] / 'fixtures' / 'orders.json').read_text())


@app.post('/api/runs')
async def start(body: Start):
    cfg = db.get('supervisors', body.supervisor_id)
    if not cfg:
        raise HTTPException(404, 'Create a supervisor first')
    id = body.order.order_id
    now = datetime.now(timezone.utc).isoformat()
    initial = {'id': id, 'workflow_id': 'order-supervisor:'+id, 'order': body.order.model_dump(),
        'config': cfg, 'order_status': 'created', 'execution_status': 'running',
        'agent_state': 'idle', 'next_wake_at': None, 'decision_count': 0,
        'latest_decision': '', 'memory': '', 'events': [], 'seen_events': [], 'timeline': [],
        'actions': [], 'instructions': [], 'issues': [], 'needs_review': False,
        'contact_requires_review': False, 'final_report': None, 'created_at': now, 'updated_at': now}
    db.put('runs', id, initial, insert_only=True)
    s = find(id)
    try:
        await app.state.temporal.start_workflow('OrderSupervisor', s, id=s['workflow_id'],
            task_queue='order-supervisor', id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE)
    except WorkflowAlreadyStartedError:
        pass
    except Exception:
        raise HTTPException(503, 'Could not start Temporal workflow. Retry the same order.')
    return find(id)


@app.get('/api/runs')
def runs():
    return db.list_rows('runs')


@app.get('/api/runs/{id}')
def run(id: str):
    return find(id)


async def signal(id, command):
    s = find(id)
    if s['execution_status'] in {'completed','terminated','failed'}:
        raise HTTPException(409, 'This run has ended')
    try:
        await app.state.temporal.get_workflow_handle(s['workflow_id']).signal('command', command)
    except Exception:
        raise HTTPException(503, 'Signal not accepted; check Temporal and retry')
    return {'status': 'accepted', 'message': 'Accepted by Temporal; dashboard updates after worker processing.'}


@app.post('/api/runs/{id}/events', status_code=202)
async def event(id: str, body: Event):
    return await signal(id, {'op': 'event', 'event': {**body.model_dump(), 'occurred_at': datetime.now(timezone.utc).isoformat()}})


@app.post('/api/runs/{id}/instructions', status_code=202)
async def instruction(id: str, body: Instruction):
    return await signal(id, {'op': 'instruction', 'instruction': body.model_dump()})


@app.post('/api/runs/{id}/{operation}', status_code=202)
async def control(id: str, operation: str):
    if operation not in {'pause','resume','interrupt','terminate'}:
        raise HTTPException(404, 'Unknown control')
    if operation != 'terminate':
        return await signal(id, {'op': operation})
    s = find(id)
    if s['execution_status'] in {'completed','terminated'}:
        return s
    handle = app.state.temporal.get_workflow_handle(s['workflow_id'])
    try:
        await handle.terminate('Stopped by operator')
    except Exception:
        description = await handle.describe()
        if description.status == WorkflowExecutionStatus.COMPLETED:
            return find(id)
        if description.status != WorkflowExecutionStatus.TERMINATED:
            raise HTTPException(503, 'Termination could not be confirmed')
    # The row lock serializes this with in-flight persistence activities.
    with db.connect() as c:
        s = c.execute('SELECT data FROM runs WHERE id=%s FOR UPDATE', (id,)).fetchone()[0]
        s['execution_status'] = 'terminated'
        s['agent_state'] = 'idle'
        s['next_wake_at'] = None
        s['final_report'] = final_report(s, partial=True)
        s['timeline'].append({'kind':'terminated','at':datetime.now(timezone.utc).isoformat(),'text':'Hard stopped. Report uses previously saved records only.'})
        c.execute('UPDATE runs SET data=%s WHERE id=%s', (db.Jsonb(s), id))
    return s
