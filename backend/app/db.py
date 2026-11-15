import os
import psycopg
from psycopg.types.json import Jsonb


def connect():
    return psycopg.connect(os.getenv('DATABASE_URL', 'postgresql://supervisor:supervisor@localhost:5432/supervisor'))


def init_db():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS supervisors (id text PRIMARY KEY, data jsonb NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS runs (id text PRIMARY KEY, data jsonb NOT NULL)')


def get(table, id):
    assert table in {'runs', 'supervisors'}
    with connect() as c:
        row = c.execute(f'SELECT data FROM {table} WHERE id=%s', (id,)).fetchone()
    return row[0] if row else None


def put(table, id, data, insert_only=False):
    assert table in {'runs', 'supervisors'}
    with connect() as c:
        if insert_only:
            c.execute(f'INSERT INTO {table} VALUES (%s,%s) ON CONFLICT DO NOTHING', (id, Jsonb(data)))
        else:
            c.execute(f'INSERT INTO {table} VALUES (%s,%s) ON CONFLICT(id) DO UPDATE SET data=EXCLUDED.data', (id, Jsonb(data)))


def list_rows(table):
    assert table in {'runs', 'supervisors'}
    with connect() as c:
        return [r[0] for r in c.execute(f'SELECT data FROM {table} ORDER BY id DESC')]
