import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from temporalio.client import Client
from temporalio.worker import Worker
from .workflows import OrderSupervisor
from .activities import save_state, decide
from .db import init_db


async def main():
    init_db()
    client = await Client.connect(os.getenv('TEMPORAL_ADDRESS', 'localhost:7233'))
    with ThreadPoolExecutor(max_workers=8) as pool:
        worker = Worker(client, task_queue='order-supervisor', workflows=[OrderSupervisor],
                        activities=[save_state, decide], activity_executor=pool)
        await worker.run()


if __name__ == '__main__':
    asyncio.run(main())
