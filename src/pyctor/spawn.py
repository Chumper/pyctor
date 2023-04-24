from contextlib import _AsyncGeneratorContextManager
from logging import getLogger
from typing import Callable, List
from uuid import uuid4

import trio

import pyctor._util
import pyctor.behavior
import pyctor.types

logger = getLogger(__name__)


class SpawnerImpl(pyctor.types.Spawner):
    _children: List[pyctor.types.Ref[None]]

    _nursery: trio.Nursery

    _dispatcher: pyctor.types.Dispatcher

    def __init__(
        self, nursery: trio.Nursery, dispatcher: pyctor.types.Dispatcher
    ) -> None:
        self._nursery = nursery
        self._dispatcher = dispatcher
        self._children = []

    def children(self) -> List[pyctor.types.Ref[None]]:
        return self._children

    def stop_all(self) -> None:
        for c in self._children:
            c.stop()

    async def spawn(
        self,
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
        options: pyctor.types.SpawnOptions | None = None,
    ) -> pyctor.types.Ref[pyctor.types.T]:
        ref = await self._dispatcher.dispatch(behavior=behavior, options=options)

        # append to child array
        self._children.append(ref)  # type: ignore
        # return the ref
        return ref
