from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Generic

import trio

from pyctor.behavior import BehaviorHandlerImpl, BehaviorProcessorImpl
from pyctor.context import SpawnMixin
from pyctor.types import Behavior, BehaviorHandler, BehaviorProcessor, LifecycleSignal, Ref, ReplyProtocol, T, U, V, Spawner


class ActorSystem(Generic[T]):
    _root_behavior: Ref[T]

    def __init__(self, root_behavior: Ref[T]) -> None:
        super().__init__()
        self._root_behavior = root_behavior

    def root(self) -> Ref[T]:
        """
        Returns the address of the root Behavior
        """
        return self._root_behavior

    async def stop(self) -> None:
        """
        Stops the actor system by sending a stop message to the root behavior
        """
        await self._root_behavior.stop()

class ActorNursery(SpawnMixin):
    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__(nursery)

@asynccontextmanager
async def root_behavior(root_behavior: Behavior[T], name: str | None = None) -> AsyncGenerator[ActorSystem[T], None]:
    # narrow class down to a BehaviorImpl
    assert isinstance(root_behavior, BehaviorHandler), "The root behavior needs to implement the BehaviorHandler"

    # root nursery that will start all actors and wait for the whole actor system to terminate
    try:
        async with trio.open_nursery() as n:
            # create a BehaviorImpl
            ref = await BehaviorProcessorImpl.create(nursery=n, behavior=root_behavior, name=name)
            actor_system = ActorSystem(ref)
            yield actor_system
    finally:
        pass

@asynccontextmanager
async def open_nursery() -> AsyncGenerator[ActorNursery, None]:
    # root nursery that will start all actors and wait for the whole actor system to terminate
    try:
        async with trio.open_nursery() as n:
            actor_system = ActorNursery(n)
            yield actor_system
    finally:
        pass

@contextmanager
def multicore_dispatcher(n: ActorNursery) -> Generator[None, None, None]:
    # root nursery that will start all actors and wait for the whole actor system to terminate
    try:
        yield None
    finally:
        pass