
import asyncio
from typing import Generic

from pyctor.behavior import Behavior
from pyctor.ref import Ref, RootRef
from pyctor.sender import Sender
from pyctor.spawner import Spawner
from pyctor.types import T


class Context(Generic[T], Spawner, Sender):
    def self(self) -> Ref[T]:
        pass
    pass

    @staticmethod
    def fromRootBehavior(behavior: Behavior[T], loop: asyncio.AbstractEventLoop = None) -> RootRef[T]:
        return RootRef(behavior, loop=loop)

