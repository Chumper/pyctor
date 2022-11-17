from contextlib import _AsyncGeneratorContextManager, _GeneratorContextManager, asynccontextmanager
from logging import getLogger
from types import FunctionType
from typing import AsyncGenerator, Callable, List
from uuid import uuid4

import trio
from pyctor.behavior import BehaviorProcessorImpl

from pyctor.types import Behavior, BehaviorHandler, Context, Ref, Spawner, T

logger = getLogger(__name__)

class SpawnMixin(Spawner):
    children: List[Ref] = []
    nursery: trio.Nursery

    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__()
        self.nursery = nursery

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
        b = BehaviorProcessorImpl(nursery=self.nursery, behavior=impl, name=name)
        # start in the nursery
        self.nursery.start_soon(b.behavior_task)
        # append to array
        self.children.append(b.ref())
        # return the ref
        return b._ref


class ContextImpl(SpawnMixin, Context[T]):
    _ref: Ref[T]

    def __init__(self, nursery: trio.Nursery, ref: Ref[T]) -> None:
        super().__init__(nursery)
        self._ref = ref

    def self(self) -> Ref[T]:
        """
        Returns the address of the Behavior belonging to this context.
        """
        return self._ref
