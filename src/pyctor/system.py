from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor.context
import pyctor.types
import pyctor.dispatch

class BehaviorNurseryImpl(pyctor.types.BehaviorNursery, pyctor.context.SpawnMixin):
    def __init__(self, nursery: trio.Nursery, options: pyctor.types.BehaviorNurseryOptions) -> None:
        dispatcher = options.dispatcher if options.dispatcher else pyctor.dispatch.SingleProcessDispatcher(nursery=nursery)
        super().__init__(nursery=nursery, dispatcher=dispatcher)


@asynccontextmanager
async def open_nursery(
    options: pyctor.types.BehaviorNurseryOptions = pyctor.types.BehaviorNurseryOptions(),
) -> AsyncGenerator[pyctor.types.BehaviorNursery, None]:
    # nursery that can start behaviors and waits for the whole system to terminate
    try:
        async with trio.open_nursery() as n:
            actor_system = BehaviorNurseryImpl(nursery=n, options=options)
            yield actor_system
    finally:
        pass
