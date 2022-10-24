
from typing import Generic
from pyctor import T
from pyctor.ref import Ref
from pyctor.sender import Sender
from pyctor.spawner import Spawner


class Context(Generic[T], Spawner, Sender):
    def self(self) -> Ref[T]:
        pass
    pass