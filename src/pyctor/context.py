from typing import Any, AsyncGenerator, Callable, List
from uuid import uuid4

import trio

import pyctor.behavior
from pyctor.types import Behavior, BehaviorHandler, BehaviorProcessor, Context, Ref, Spawner, T


class SpawnMixin(Spawner):
    children: List[Ref] = []
    nursery: trio.Nursery

    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__()
        self.nursery = nursery

    async def spawn(self, behavior: Callable[[],AsyncGenerator[Behavior[T], None]] | Behavior[T], name: str = str(uuid4())) -> Ref[T]:
        match behavior:
            case BehaviorHandler():
                pass
            case function():
                pass
            case _:
                raise ValueError("behavior needs to implement the Behavior or the Generator Protocol")

        # narrow class down to a BehaviorProtocol
        assert isinstance(behavior, (Callable[[],AsyncGenerator], BehaviorHandler)), "behavior needs to implement the BehaviorProtocol"
        # create the process
        b = pyctor.behavior.BehaviorProcessorImpl(nursery=self.nursery, behavior=behavior, name=name)
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
