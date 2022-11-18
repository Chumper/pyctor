from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from logging import getLogger
from types import FunctionType
from typing import AsyncGenerator, Callable, List
from uuid import uuid4

import trio

import pyctor.behavior
import pyctor.types

logger = getLogger(__name__)


class SpawnMixin(pyctor.types.Spawner):
    _children: List[pyctor.types.Ref[None]] = []

    _nursery: trio.Nursery

    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__()
        self._nursery = nursery

    def children(self) -> List[pyctor.types.Ref[None]]:
        return self._children

    async def stop(self) -> None:
        for c in self._children:
            await c.stop()

    async def spawn(
        self,
        behavior: Callable[[], _AsyncGeneratorContextManager[pyctor.types.Behavior[pyctor.types.T]]] | pyctor.types.Behavior[pyctor.types.T],
        name: str = str(uuid4()),
    ) -> pyctor.types.Ref[pyctor.types.T]:
        impl: Callable[[], _AsyncGeneratorContextManager[pyctor.types.BehaviorHandler[pyctor.types.T]]]
        match behavior:
            case pyctor.types.BehaviorHandler():
                logger.debug("Creating ContextManager from single Behavior")

                @asynccontextmanager
                async def f() -> AsyncGenerator[pyctor.types.BehaviorHandler[pyctor.types.T], None]:
                    yield behavior

                impl = f
            case FunctionType():
                logger.debug("Using ContextManager from Function")
                impl = behavior
            case _:
                raise ValueError("behavior needs to implement the Behavior or the Generator Protocol")

        # create the process
        b = pyctor.behavior.BehaviorProcessorImpl[pyctor.types.T](
            nursery=self._nursery,
            behavior=impl,
            name=name,
        )
        # start in the nursery
        self._nursery.start_soon(b.behavior_task)
        # append to array
        self._children.append(b.ref())  # type: ignore
        # return the ref
        return b.ref()
