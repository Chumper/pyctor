from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generic

import trio

from pyctor.behavior import BehaviorHandlerImpl, BehaviorProcessorImpl
from pyctor.types import Behavior, BehaviorHandler, BehaviorProcessor, LifecycleSignal, Ref, ReplyProtocol, T, U, V


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

    def stop(self) -> None:
        """
        Stops the actor system by sending a stop message to the root behavior
        """
        self._root_behavior.stop()


@asynccontextmanager
async def actor_system(root_behavior: Behavior[T], name: str | None = None) -> AsyncGenerator[ActorSystem[T], None]:
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