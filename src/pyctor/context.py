from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from logging import getLogger
from types import FunctionType
from typing import AsyncGenerator, Callable, List
from uuid import uuid4

import trio

from pyctor.behavior import BehaviorProcessorImpl
from pyctor.types import ActorNursery, Behavior, BehaviorHandler, Ref, Spawner, T

logger = getLogger(__name__)

class SpawnMixin(Spawner):
    _children: List[Ref] = []
    _nursery: ActorNursery

    def __init__(self, nursery: ActorNursery) -> None:
        super().__init__()
        self._nursery = nursery

    async def spawn(
        self,
        behavior: Callable[[], _AsyncGeneratorContextManager[Behavior[T]]] | Behavior[T],
        name: str = str(uuid4()),
    ) -> Ref[T]:
        impl: Callable[[], _AsyncGeneratorContextManager[BehaviorHandler[T]]]
        match behavior:
            case BehaviorHandler():
                logger.debug("Creating ContextManager from single Behavior")
                @asynccontextmanager
                async def f() -> AsyncGenerator[BehaviorHandler[T], None]:
                    yield behavior
                impl = f
            case FunctionType():
                logger.debug("Using ContextManager from Function")
                impl = behavior
            case _:
                raise ValueError(
                    "behavior needs to implement the Behavior or the Generator Protocol"
                )

        # create the process
        b = BehaviorProcessorImpl(nursery=self._nursery, behavior=impl, name=name)
        # start in the nursery
        self._nursery.start_soon(b.behavior_task)
        # append to array
        self.children.append(b.ref())
        # return the ref
        return b._ref
