from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

from pyctor.context import SpawnMixin


class ActorNursery(SpawnMixin):
    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__(nursery)


@asynccontextmanager
async def open_nursery() -> AsyncGenerator[ActorNursery, None]:
    # root nursery that will start all actors and wait for the whole actor system to terminate
    try:
        async with trio.open_nursery() as n:
            actor_system = ActorNursery(n)
            yield actor_system
    finally:
        pass