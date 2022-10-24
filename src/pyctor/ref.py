import asyncio
from typing import Generic

from pyctor.behavior import Behavior, BehaviorImplementation
from pyctor.types import T


class Ref(Generic[T]):
    _impl: BehaviorImplementation[T]

    def __init__(self, behavior: Behavior[T]) -> None:
        super().__init__()
        self._impl = BehaviorImplementation(behavior)


    def send(self, msg: T) -> None:
        self._impl.send(msg)

class RootRef(Ref[T]):
    _loop: asyncio.AbstractEventLoop
    _task: asyncio.Task

    def __init__(self, behavior: Behavior[T], loop: asyncio.AbstractEventLoop | None) -> None:
        super().__init__(behavior=behavior)
        if not loop:
            self._loop = asyncio.new_event_loop()
        else:
            self._loop = loop
        self._task = self._loop.create_task(self._impl.run())

    def stop(self) -> None:
        self._impl._stopped = True
        if self._loop:
            self._loop.close()
