from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generic

import trio

from pyctor.behavior import Behavior, BehaviorImpl, BehaviorProcessor, LifecycleSignal, Ref
from pyctor.types import T


class ActorSystem(Generic[T]):
    _root_behavior: BehaviorProcessor[T]
    _nursery: trio.Nursery

    def __init__(self, root_behavior: BehaviorProcessor[T], nursery: trio.Nursery) -> None:
        super().__init__()
        self._root_behavior = root_behavior
        self._nursery = nursery

    def root(self) -> Ref[T]:
        return self._root_behavior._ref

    async def stop(self) -> None:
        """
        Stops the actor system by sending a stop message to the root behavior
        """
        await self._root_behavior.handle(LifecycleSignal.Stopped)

@asynccontextmanager
async def actor_system(root_behavior: Behavior[T], name: str = None) -> AsyncGenerator[ActorSystem[T], None]:
    # narrow class down to a BehaviorProtocol
    assert isinstance(root_behavior, BehaviorImpl), "root behavior needs to implement the BehaviorProtocol"

    # root nursery that will start all actors and wait for the whole actor system to terminate
    try:
        async with trio.open_nursery() as n:
            # create a BehaviorImpl
            b = BehaviorProcessor(behavior=root_behavior, name=name)
            actor_system = ActorSystem(b, n)
            # start the root task
            n.start_soon(b.behavior_task)
            yield actor_system
    finally:
        pass
                
