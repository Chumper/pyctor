

from typing import List

import trio

import pyctor.behavior
from pyctor.types import Behavior, BehaviorHandler, BehaviorProcessor, Context, Ref, Spawner, T


class SpawnMixin(Spawner[T]):
    _children: List[BehaviorProcessor] = []
    _nursery: trio.Nursery

    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__()
        self._nursery = nursery

    async def spawn(self, behavior: Behavior[T]) -> Ref[T]:
        # narrow class down to a BehaviorProtocol
        assert isinstance(
            behavior, BehaviorHandler
        ), "behavior needs to implement the BehaviorProtocol"
        # create the process
        b = pyctor.behavior.BehaviorProcessorImpl(nursery=self._nursery, behavior=behavior)
        # start in the nursery
        self._nursery.start_soon(b.behavior_task)
        # append to array
        self._children.append(b)
        # return the ref
        return b._ref

class ContextImpl(SpawnMixin[T], Context[T]):
    _nursery: trio.Nursery
    _ref: Ref[T]

    def __init__(self, nursery: trio.Nursery, ref: Ref[T]) -> None:
        super().__init__(nursery)
        self._nursery = nursery
        self._ref = ref

    def self(self) -> Ref[T]:
        """
        Returns the address of the Behavior belonging to this context.
        """
        return self._ref

    def nursery(self) -> trio.Nursery:
        return self._nursery