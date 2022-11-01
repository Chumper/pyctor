from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from typing import AsyncGenerator, Generic

import trio
from pyctor.behavior import Behavior, BehaviorHandler, BehaviorImpl, Ref
from pyctor.types import T


class ActorSystem(Generic[T]):
    _root_behavior: BehaviorImpl[T]
    _nursery: trio.Nursery

    def __init__(self, root_behavior: BehaviorImpl[T], nursery: trio.Nursery) -> None:
        super().__init__()
        self._root_behavior = root_behavior
        self._nursery = nursery

    def root(self) -> Ref[T]:
        return self._root_behavior._ref

    def stop(self) -> None:
        """
        Stops the actor system immediately
        """
        self._nursery.cancel_scope.cancel()

@asynccontextmanager
async def actor_system(root_behavior: Behavior[T]) -> AsyncGenerator[ActorSystem[T], None]:
    # root nursery that will start all actors and wait for the whole actor system to terminate
    try:
        async with trio.open_nursery() as n:
            # create a BehaviorImpl
            assert isinstance(root_behavior, BehaviorHandler)
            b = BehaviorImpl[T](behavior=root_behavior)
            actor_system = ActorSystem(b, n)
            # start the root task
            n.start_soon(b.behavior_task)
            yield actor_system
    finally:
        print("Actor System is shutting down")
                
