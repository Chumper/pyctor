from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor.context
import pyctor.types


class ActorNurseryImpl(pyctor.types.ActorNursery, pyctor.context.SpawnMixin):
    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__(nursery)


@asynccontextmanager
async def open_nursery() -> AsyncGenerator[pyctor.types.ActorNursery, None]:
    # root nursery that will start all actors and wait for the whole actor system to terminate
    try:
        async with trio.open_nursery() as n:
            actor_system = ActorNurseryImpl(n)
            yield actor_system
    finally:
        pass
