

from typing import List
import trio
import pyctor.behavior
from pyctor.types import T, Behavior, BehaviorHandler, BehaviorProcessor, Context, Ref, Spawner

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
        b = pyctor.behavior.BehaviorProcessorImpl(behavior=behavior)
        # start in the nursery
        self._nursery.start_soon(b.behavior_task)
        # append to array
        self._children.append(b)
        # return the ref
        return b._ref

class ContextImpl(SpawnMixin[T], Context[T]):
    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__(nursery)

    def self(self) -> Ref[T]:
        """
        Returns the address of the Behavior belonging to this context.
        """
        ...