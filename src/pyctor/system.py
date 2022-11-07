from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generic

import trio

from pyctor.behavior import BehaviorHandlerImpl, BehaviorProcessorImpl
from pyctor.types import T, U, V, Behavior, BehaviorHandler, BehaviorProcessor, LifecycleSignal, Ref, ReplyProtocol


class ActorSystem(Generic[T]):
    _root_behavior: BehaviorProcessor[T]
    _nursery: trio.Nursery

    def __init__(self, root_behavior: BehaviorProcessor[T], nursery: trio.Nursery) -> None:
        super().__init__()
        self._root_behavior = root_behavior
        self._nursery = nursery

    def root(self) -> Ref[T]:
        """
        Returns the address of the root Behavior
        """
        return self._root_behavior.ref()

    async def stop(self) -> None:
        """
        Stops the actor system by sending a stop message to the root behavior
        """
        await self._root_behavior.handle(LifecycleSignal.Stopped)
    
    async def ask(self, ref: Ref[U], msg: ReplyProtocol[V]) -> V:  # type: ignore
        # spawn actor that accepts T 
        # send message
        # wait for T, use cancelscope from Trio if needed
        # return T
        pass

@asynccontextmanager
async def actor_system(root_behavior: Behavior[T], name: str | None = None) -> AsyncGenerator[ActorSystem[T], None]:
    # narrow class down to a BehaviorImpl
    assert isinstance(root_behavior, BehaviorHandler), "The root behavior needs to implement the BehaviorHandler"

    # root nursery that will start all actors and wait for the whole actor system to terminate
    try:
        async with trio.open_nursery() as n:
            # create a BehaviorImpl
            b = BehaviorProcessorImpl(behavior=root_behavior, name=name)
            actor_system = ActorSystem(b, n)
            # start the root task
            n.start_soon(b.behavior_task)
            yield actor_system
    finally:
        pass