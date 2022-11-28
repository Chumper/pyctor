from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from logging import getLogger
from types import FunctionType
from typing import AsyncGenerator, Callable, List
from uuid import uuid4

import trio

import pyctor._util
import pyctor.behavior
import pyctor.types

logger = getLogger(__name__)


class SpawnMixin(pyctor.types.Spawner):
    _children: List[pyctor.types.Ref[None]] = []

    _nursery: trio.Nursery

    _dispatcher: pyctor.types.Dispatcher

    def __init__(self, nursery: trio.Nursery, dispatcher: pyctor.types.Dispatcher) -> None:
        super().__init__()
        self._nursery = nursery
        self._dispatcher = dispatcher

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

        impl = pyctor._util.to_contextmanager(behavior)
        ref = await self._dispatcher.dispatch(behavior=impl, name=name)

        # append to array
        self._children.append(ref)  # type: ignore
        # return the ref
        return ref
